"""
Flask-based HTTP entry point for the Varity search service.

Provides /health, /search, and /enrich endpoints.
"""

import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------- #
# Flask HTTP entry point
# ---------------------------------------------------------------------- #

_MAX_QUERY_LENGTH = 1000
_MIN_LIMIT = 1
_MAX_LIMIT = 100
_MIN_CERTAINTY = 0.0
_MAX_CERTAINTY = 1.0


def _create_app():
    """Create and configure the Flask application."""
    from flask import Flask, request, jsonify
    from functools import wraps

    app = Flask(__name__)

    # ----- CORS -----
    @app.after_request
    def _add_cors_headers(response):
        allowed_origins = os.getenv("VARITY_CORS_ORIGINS", "*")
        response.headers["Access-Control-Allow-Origin"] = allowed_origins
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    # ----- Rate limiting -----
    _rate_limit_store: Dict[str, List] = {}

    def _is_rate_limited(key: str, max_requests: int = 60, window: int = 60) -> bool:
        """Simple in-memory sliding-window rate limiter."""
        import time
        now = time.time()
        if key not in _rate_limit_store:
            _rate_limit_store[key] = []
        # Prune old entries
        _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > now - window]
        if len(_rate_limit_store[key]) >= max_requests:
            return True
        _rate_limit_store[key].append(now)
        return False

    # ----- API key auth middleware -----
    def _require_api_key(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = os.getenv("VARITY_API_KEY", "")
            if not api_key:
                # No key configured => auth disabled
                return f(*args, **kwargs)
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            else:
                token = auth_header
            if token != api_key:
                return jsonify({"error": "Unauthorized"}), 401
            return f(*args, **kwargs)
        return decorated

    # Lazy-init the semantic search engine (loaded once on first request)
    _search_engine: Dict[str, Any] = {}

    def _get_engine():
        if "instance" not in _search_engine:
            from src.weaviate_semantic_search import VaritySemanticSearch
            config_path = os.getenv("VARITY_CONFIG", "config/weaviate_config.yaml")
            profile = os.getenv("VARITY_PROFILE", "default")
            _search_engine["instance"] = VaritySemanticSearch(
                config_path=config_path, profile=profile
            )
        return _search_engine["instance"]

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint (no auth required)."""
        try:
            engine = _get_engine()
            connected = engine.client.is_connected()
            return jsonify({"status": "healthy" if connected else "degraded"}), 200
        except Exception as e:
            return jsonify({"status": "unhealthy", "error": str(e)}), 503

    @app.route("/search", methods=["POST"])
    @_require_api_key
    def search_endpoint():
        """Search endpoint accepting JSON body with query parameters."""
        # Rate limit by client IP
        client_ip = request.remote_addr or "unknown"
        if _is_rate_limited(client_ip):
            return jsonify({"error": "Rate limit exceeded"}), 429

        data = request.get_json(silent=True) or {}
        query_text = data.get("query", "").strip()
        if not query_text:
            return jsonify({"error": "Missing 'query' field"}), 400
        if len(query_text) > _MAX_QUERY_LENGTH:
            return jsonify({"error": f"Query exceeds max length of {_MAX_QUERY_LENGTH}"}), 400

        search_type = data.get("type", "Occupation")
        if search_type not in ("Occupation", "Skill"):
            return jsonify({"error": "type must be 'Occupation' or 'Skill'"}), 400

        try:
            limit = int(data.get("limit", 10))
        except (ValueError, TypeError):
            return jsonify({"error": "limit must be an integer"}), 400
        limit = max(_MIN_LIMIT, min(limit, _MAX_LIMIT))

        try:
            certainty = float(data.get("certainty", 0.7))
        except (ValueError, TypeError):
            return jsonify({"error": "certainty must be a number"}), 400
        if not (_MIN_CERTAINTY <= certainty <= _MAX_CERTAINTY):
            return jsonify({"error": "certainty must be between 0.0 and 1.0"}), 400

        try:
            engine = _get_engine()
            if search_type == "Skill":
                results = engine.search_skills_by_text(
                    query_text, limit=limit, similarity_threshold=certainty
                )
            else:
                results = engine.search_occupations_by_text(
                    query_text, limit=limit, similarity_threshold=certainty
                )
            return jsonify({"results": results, "count": len(results)})
        except Exception:
            logger.exception("Search failed")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/enrich", methods=["POST"])
    @_require_api_key
    def enrich_endpoint():
        """Enrich a job posting with ESCO taxonomy data."""
        client_ip = request.remote_addr or "unknown"
        if _is_rate_limited(client_ip, max_requests=20, window=60):
            return jsonify({"error": "Rate limit exceeded"}), 429

        data = request.get_json(silent=True) or {}
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        if not title or not description:
            return jsonify({"error": "Both 'title' and 'description' are required"}), 400
        if len(title) > _MAX_QUERY_LENGTH or len(description) > 5000:
            return jsonify({"error": "Input exceeds maximum length"}), 400

        try:
            engine = _get_engine()
            result = engine.enrich_job_posting(title, description)
            return jsonify(engine.get_enrichment_summary(result))
        except Exception:
            logger.exception("Enrichment failed")
            return jsonify({"error": "Enrichment failed"}), 500

    return app


def main():
    """Entry point for the search service."""
    port = int(os.getenv("VARITY_SEARCH_PORT", "8000"))
    host = os.getenv("VARITY_SEARCH_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    app = _create_app()
    logger.info(f"Starting Varity search service on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
