from abc import ABC, abstractmethod


class IDisposable(ABC):
    @abstractmethod
    def try_init(self, bucket_name: str, object_name: str):
        """Initialize local variable with data"""
        pass

    # @abstractmethod
    # def dispose(self):
    #     """Clear memory off the local variable"""
    #     pass
