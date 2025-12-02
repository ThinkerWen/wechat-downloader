class CrawlerException(Exception):
    """Base exception for crawler errors."""
    pass

class DecryptError(CrawlerException):
    """Exception raised for errors in the decryption process."""
    pass

class DownloadError(CrawlerException):
    """Exception raised for errors during the download process."""
    pass

class NetworkError(CrawlerException):
    """Exception raised for network-related errors."""
    pass

class UnhandledError(CrawlerException):
    """Exception raised for unhandled errors."""
    pass
