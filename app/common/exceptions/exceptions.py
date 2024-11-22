"""
Exceptions module goal is to create custom exceptions in order to raise propper errors,
which will make understandable problems for users.
"""


class BaseError(KeyError):
    def __init__(self, *args):
        """
        Initializes the object with an optional message.

        Args:
            *args: An optional message to be stored in the object. If provided, it should be a single argument.

        Returns:
            None
        """
        if args:
            self.message = args[0]
        else:
            self.message = None


class TimeOutError(BaseError):
    def __str__(self):
        """
        A method that returns a custom string representation for the TimeOutError class.
        """
        if self.message:
            return "TimeOutError, {0} ".format(self.message)
        else:
            return (
                "Timeout time exceeded:("
            )


class NoDataError(BaseError):
    def __str__(self):
        """
        Returns a string representation of the NoDataError object. If the object has a message attribute, it returns a formatted string with the message. Otherwise, it returns the string "No Data in DB".

        Returns:
            str: The string representation of the NoDataError object.
        """
        if self.message:
            return f"No existing data in DB for: {self.message}"
        else:
            return "No Data in DB"
