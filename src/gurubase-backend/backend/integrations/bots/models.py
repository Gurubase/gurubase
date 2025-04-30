class BotContext:

    class Type:
        GITHUB = "github"
        SLACK = "slack"
        DISCORD = "discord"

    def __init__(self, type: Type, data: list):
        self.type = type
        self.data = data

    def __str__(self):
        return f"{self.type}: {self.data}"

    def __repr__(self):
        return self.__str__()
