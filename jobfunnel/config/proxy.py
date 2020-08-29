"""Proxy configuration for Session()
"""
from jobfunnel.config import BaseConfig


class ProxyConfig(BaseConfig):
    """Simple config object to contain proxy configuration
    """
    def __init__(self, protocol: str, ip_address: str, port: int) -> None:
        self.protocol = protocol
        self.ip_address = ip_address
        self.port = port

    @property
    def url(self) -> str:
        """Get the url string for use in a Session.proxies object
        """
        url_str = ''
        if self.protocol != '':
            url_str += self.protocol + '://'
        if self.ip_address != '':
            url_str += self.ip_address
        if self.port != '':
            url_str += ':' + self.port
        return url_str  # FIXME: this could be done in one line

    def validate(self) -> None:
        """TODO: impl. validate ip addr is valid format etc"""
        pass
