"""Short-lived server-side authorization for accepting Socket.IO invitations."""

from threading import Lock
import time


class SocketInviteRegistry:
    def __init__(self, ttl_seconds=300, clock=None):
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._clock = clock or time.monotonic
        self._lock = Lock()
        self._invites = {}

    def _remove_expired(self, now):
        for key, invite in list(self._invites.items()):
            if invite["expires_at"] <= now:
                self._invites.pop(key, None)

    def issue(self, kind, recipient_sid, sender_sid, sender_char_id, recipient_char_id, context=None):
        values = (kind, recipient_sid, sender_sid, sender_char_id, recipient_char_id)
        if any(value in (None, "") for value in values):
            return False

        now = self._clock()
        key = (str(kind), str(recipient_sid), str(sender_char_id))
        invite = {
            "kind": str(kind),
            "recipient_sid": str(recipient_sid),
            "sender_sid": str(sender_sid),
            "sender_char_id": str(sender_char_id),
            "recipient_char_id": str(recipient_char_id),
            "context": dict(context or {}),
            "expires_at": now + self._ttl_seconds,
        }
        with self._lock:
            self._remove_expired(now)
            self._invites[key] = invite
        return True

    def consume(self, kind, recipient_sid, recipient_char_id, sender_char_id=None, context=None):
        now = self._clock()
        expected_context = dict(context or {})
        with self._lock:
            self._remove_expired(now)
            for key, invite in list(self._invites.items()):
                if invite["kind"] != str(kind):
                    continue
                if invite["recipient_sid"] != str(recipient_sid):
                    continue
                if invite["recipient_char_id"] != str(recipient_char_id):
                    continue
                if sender_char_id is not None and invite["sender_char_id"] != str(sender_char_id):
                    continue
                if any(invite["context"].get(name) != value for name, value in expected_context.items()):
                    continue
                self._invites.pop(key, None)
                return dict(invite)
        return None

    def discard_socket(self, sid):
        sid = str(sid)
        with self._lock:
            for key, invite in list(self._invites.items()):
                if sid in (invite["recipient_sid"], invite["sender_sid"]):
                    self._invites.pop(key, None)
