class PromptfulError(Exception):
    """Base class for every error raised by the Promptful SDK."""


class PromptfulConnectionError(PromptfulError):
    """The API could not be reached (network failure, timeout, DNS, ...)."""


class PromptfulAPIError(PromptfulError):
    """The API responded with an unexpected error status."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API request failed with {status_code}: {detail}")


class PromptNotFoundError(PromptfulError):
    """No Prompt has a Live Version at the given slug."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"no prompt found at slug {slug!r}")


class PromptConflictError(PromptfulError):
    """A concurrent write landed on this slug between resolving and deleting it.

    Raised by `Client.delete_prompt` when the Live Version it resolved is no
    longer current by the time the delete lands (see ADR-0003, ADR-0008). Not
    retried automatically — call `delete_prompt` again if the delete should
    still happen.
    """

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"a concurrent write changed {slug!r}; re-check and retry")
