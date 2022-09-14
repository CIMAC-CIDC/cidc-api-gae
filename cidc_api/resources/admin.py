from flask import Blueprint
from ..csms import get_with_authorization as csms_get
from ..models import CIDCRole
from ..shared.auth import requires_auth

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/test_csms", methods=["GET"])
@requires_auth("admin", [CIDCRole.ADMIN.value])
def test_csms():
    return csms_get("/doc").json()
