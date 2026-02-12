"""HTTP utility functions for AJAX request handling."""

from flask import request, jsonify


def is_ajax_request():
    """Check if request is AJAX/modal request."""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json


def json_response(success, message=None, error=None, **kwargs):
    """Create JSON response for AJAX requests."""
    response_data = {'success': success}
    if message:
        response_data['message'] = message
    if error:
        response_data['error'] = error
    response_data.update(kwargs)
    status_code = 200 if success else 400
    return jsonify(response_data), status_code
