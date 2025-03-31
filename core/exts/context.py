from discord.ext import commands


class Context(commands.Context):
    async def reply(self, content=None, mention_author=False, **kwargs):
        return await super().reply(content, **kwargs)


async def get_context_without_mention(self, message, *, cls=Context):
    return await super(type(self), self).get_context(message, cls=cls)


def setup(bot):
    bot.get_context = get_context_without_mention.__get__(bot, type(bot))
