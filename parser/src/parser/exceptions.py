class RozetkaError(Exception):
    """Base exception for all Rozetka scraper errors."""
    pass

class BrowserNotInitializedError(RozetkaError):
    """Raised when browser or context is not initialized."""
    pass

class ProductCardsNotFoundError(RozetkaError):
    """Raised when product cards are not found on the page."""
    pass

class ProductsListEmptyError(RozetkaError):
    """Raised when the products list is empty for a category."""
    pass

class TargetProductNotFoundError(RozetkaError):
    """Raised when the target product is not found in the category."""
    pass

class AdvertisementBlockNotFoundError(RozetkaError):
    """Raised when the advertisement block is not found on the page."""
    pass

class BoundingBoxError(RozetkaError):
    """Raised when failing to get the bounding box for an element."""
    pass

class DuplicateObjectError(RozetkaError):
    """Raised when an object already exists in the database."""
    pass
