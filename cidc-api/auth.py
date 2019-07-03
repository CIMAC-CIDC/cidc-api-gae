<<<<<<< HEAD
=======
import json
>>>>>>> Clean up BearerAuth class and add auth tests
import logging
from typing import List

import requests
from eve.auth import TokenAuth
from jose import jwt

from models import Users
<<<<<<< HEAD
from settings import AUTH0_DOMAIN, ALGORITHMS, AUTH0_CLIENT_ID
=======
from settings import AUTH0_AUDIENCE, AUTH0_DOMAIN, ALGORITHMS, AUTH0_CLIENT_ID
>>>>>>> Clean up BearerAuth class and add auth tests


logger = logging.getLogger("cidc-api.auth")


class AuthError(ValueError):
    def __init__(self, error_code: str, message: str, status_code: int = 401):
        """
        An error resulting in a failure to authenticate a user.

        Args:
            error_code: an error code, e.g., 'token_expired'
            message: a human-friendly description of the error
            status_code: the HTTP status code to include in the response
        """
        self.error_code = error_code
        self.message = message
        self.status_code = status_code

<<<<<<< HEAD
    def json(self):
        return {"error_code": self.error_code, "message": self.message}
=======
    def __str__(self):
        return json.dumps({"error_code": self.error_code, "message": self.message})
>>>>>>> Clean up BearerAuth class and add auth tests


class BearerAuth(TokenAuth):
    """
    Handles bearer token authorization.
    """

    def check_auth(
        self, id_token: str, allowed_roles: List[str], resource: str, method: str
    ) -> bool:
        """
        Validates the user's id_token, extracts user info if valid.
        If this is a registration attempt, create 

        Args:
            id_token: A JWT id_token
            allowed_roles: Array of strings of user roles
            resource: Endpoint being accessed
            method: HTTP method (GET, POST, PATCH, DELETE)
        
        Returns:
            bool: True if the user successfully authenticated, False otherwise.
        
        TODO: role-based resource/method-level authorization
        """
        profile = self.token_auth(id_token)

        Users.find_or_create(profile["email"])

        return True

    def token_auth(self, id_token: str) -> dict:
        """
        Checks if the supplied id_token is valid, and, if so,
        decodes and returns its payload.

        Args:
            id_token: a JWT id_token.

        Returns:
            dict: the user's decoded profile info.

        TODO: implement token caching
        """
        public_key = self.get_issuer_public_key(id_token)

        payload = self.decode_id_token(id_token, public_key)

        logger.info("Authenticated user: " + payload["email"])

        return payload

    def get_issuer_public_key(self, token: str) -> dict:
        """
        Get the appropriate public key to check this token for authenticity.

        Args:
            token: an encoded JWT.
        
        Raises:
            AuthError: if no public key can be found.
            
        Returns:
            str: the public key.
        """
        try:
            header = jwt.get_unverified_header(token)
        except jwt.JWTError as e:
            raise AuthError("invalid_signature", str(e))

        # Get public keys from our Auth0 domain
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        jwks = requests.get(jwks_url).json()

        # Obtain the public key used to sign this token
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == header["kid"]:
                public_key = key

        # If no matching public key was found, we can't validate the token
        if not public_key:
            raise AuthError(
                "no_public_key", "Found no public key with id %s" % header["kid"]
            )

        return public_key

    def decode_id_token(self, token: str, public_key: dict) -> dict:
        """
        Decodes the token and checks it for validity.

        Args:
            token: the JWT to validate and decode
            public_key: public_key

        Raises:
            AuthError: 
                - if token is expired
                - if token has invalid claims
                - if token signature is invalid in any way

        Returns:
            dict: the decoded token as a dictionary.
        """
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=ALGORITHMS,
<<<<<<< HEAD
                # TODO: is this what we want?
                audience=AUTH0_CLIENT_ID,
=======
                audience=AUTH0_AUDIENCE,
>>>>>>> Clean up BearerAuth class and add auth tests
                issuer=f"https://{AUTH0_DOMAIN}/",
                options={"verify_at_hash": False},
            )
        except jwt.ExpiredSignatureError as e:
            raise AuthError("expired_token", str(e))
        except jwt.JWTClaimsError as e:
            raise AuthError("invalid_claims", str(e))
        except jwt.JWTError as e:
            raise AuthError("invalid_signature", str(e))

        # Currently, only id_tokens are accepted for authentication.
        # Going forward, we could also accept access tokens that we
        # use to query the userinfo endpoint.
        if "email" not in payload:
            msg = "An id_token with an 'email' field is required to authenticate"
            raise AuthError("id_token_required", msg)

        return payload
