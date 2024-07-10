from __future__ import annotations
from __future__ import annotations

from aiogram import types as aiogram_types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pyrogram import enums as pyro_enums
from pyrogram import types as pyro_types
from pyrogram import utils as pyro_utils
from telethon.tl.custom import Message as TelethonMessage
from telethon.tl.types import (
    Poll,
    PollResults,
    PollAnswerVoters,
    ReplyInlineMarkup,
    User, MessageReplyHeader
)

from tele_bridge.bases.message import MessageObject


class TelethonMessageObjectMixin:
    @classmethod
    def _parse_poll(cls, message: TelethonMessage) -> pyro_types.Poll | None:
        media_poll = message.poll
        if not media_poll:
            return None
        client = message._client
        poll: Poll = media_poll.poll
        poll_results: PollResults = media_poll.results
        results: list[PollAnswerVoters] = poll_results.results

        chosen_option_id = None
        correct_option_id = None
        options = []

        for i, answer in enumerate(poll.answers):
            voter_count = 0

            if results:
                result = results[i]
                voter_count = result.voters

                if result.chosen:
                    chosen_option_id = i

                if result.correct:
                    correct_option_id = i

            options.append(
                pyro_types.PollOption(
                    text=answer.text,
                    voter_count=voter_count,
                    data=answer.option,
                    client=client
                )
            )

        return pyro_types.Poll(
            id=str(poll.id),
            question=poll.question,
            options=options,
            total_voter_count=media_poll.results.total_voters,
            is_closed=poll.closed,
            is_anonymous=not poll.public_voters,
            type=pyro_enums.PollType.QUIZ if poll.quiz else pyro_enums.PollType.REGULAR,
            allows_multiple_answers=poll.multiple_choice,
            chosen_option_id=chosen_option_id,
            correct_option_id=correct_option_id,
            explanation=poll_results.solution,
            explanation_entities=[
                pyro_types.MessageEntity._parse(client, i, {})
                for i in poll_results.solution_entities
            ] if poll_results.solution_entities else None,
            open_period=poll.close_period,
            close_date=pyro_utils.timestamp_to_datetime(poll.close_date),
            client=client
        )


class TelethonMessageObject(MessageObject, TelethonMessageObjectMixin):

    def __init__(self, message: TelethonMessage):
        super().__init__(message)
        self.m = message

    def get_text(self):
        return self.m.raw_text

    def get_html_text(self):
        return self.m.text

    def have_from_user(self):
        if isinstance(self.m.sender, User):
            return True

    def get_first_name(self):
        if isinstance(self.m.sender, User):
            return self.m.sender.first_name

    def get_last_name(self):
        if isinstance(self.m.sender, User):
            return self.m.sender.last_name

    def get_chat_id(self):
        return self.m.chat_id

    def get_chat_username(self):
        return self.m.chat.username

    def get_user_username(self):
        if isinstance(self.m.sender, User):
            return self.m.sender.username

    def get_user_id(self):
        if isinstance(self.m.sender, User):
            return self.m.sender_id

    def get_message_id(self):
        return self.m.id

    def get_reply_to_message_id(self):
        if isinstance(self.m.reply_to, MessageReplyHeader):
            return self.m.reply_to.reply_to_msg_id

    def get_message_link(self):
        username = self.get_chat_username()
        msg_id = self.get_message_id()
        if username:
            return f"https://t.me/{username}/{msg_id}"
        else:
            chat_id = self.get_chat_id()
            return f"https://t.me/c/{chat_id}/{msg_id}"

    def has_media(self) -> bool:
        return bool(self.m.media)

    def get_media_group_id(self):
        return self.m.grouped_id

    def get_poll(self) -> pyro_types.Poll:
        return self._parse_poll(self.m)

    def get_media_file_size(self):
        return self.m.file.size if self.m.file else None

    def get_media_file_id(self) -> str | None:
        if self.m.photo:
            return self.m.photo.id
            # sizes = self.m.photo.sizes
            # sizes.sort(key=lambda p: p.size if hasattr(p, 'size') else 0)
            # return sizes[-1].file_id

        return self.m.file.id if self.m.file else None

    def get_media_type(self):
        media_type = None
        if self.m.photo:
            media_type = pyro_enums.MessageMediaType.PHOTO
        elif self.m.video:
            media_type = pyro_enums.MessageMediaType.VIDEO
        elif self.m.gif:
            media_type = pyro_enums.MessageMediaType.ANIMATION
        elif self.m.audio:
            media_type = pyro_enums.MessageMediaType.AUDIO
        elif self.m.voice:
            media_type = pyro_enums.MessageMediaType.VOICE
        elif self.m.video_note:
            media_type = pyro_enums.MessageMediaType.VIDEO_NOTE
        elif self.m.document:
            media_type = pyro_enums.MessageMediaType.DOCUMENT
        elif self.m.sticker:
            media_type = pyro_enums.MessageMediaType.STICKER
        elif self.m.poll:
            media_type = pyro_enums.MessageMediaType.POLL
        elif self.m.contact:
            media_type = pyro_enums.MessageMediaType.CONTACT
        elif self.m.geo:
            media_type = pyro_enums.MessageMediaType.LOCATION
        elif self.m.venue:
            media_type = pyro_enums.MessageMediaType.VENUE
        elif self.m.game:
            media_type = pyro_enums.MessageMediaType.GAME

        return media_type

    def get_file_name(self) -> str | None:
        return self.m.file.name if self.m.file else None

    def get_reply_markup(self) -> aiogram_types.InlineKeyboardButton | None:
        if isinstance(self.m.reply_markup, ReplyInlineMarkup):
            inline_builder = InlineKeyboardBuilder()
            for row in self.m.reply_markup.rows:
                inline_builder.add(
                    *[aiogram_types.InlineKeyboardButton(
                        text=button.text,
                        url=button.url,
                    ) for button in row.buttons]
                )
        return None
