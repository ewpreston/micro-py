import json
import os
import sys

from app.redis_connection import RedisConnection
from redis import ResponseError

STREAM_NAME = os.getenv("REDIS_USER_STREAM", "new_user")


class NewUserService:
    redis = RedisConnection.get_client()

    @classmethod
    def read_stream(cls, last_entry_id):
        # Algorithm:
        #
        # * Perform a blocking read on the stream at KEY_NAME, to get
        #   the one entry from it. Start reading using the supplied value
        #   of lastEntryId which is stream ID 0-0. Remember you will need
        #   to store the ID of the last entry read each time you read
        #   an entry off of the stream, then use that in the next call
        #   to XREAD.
        # * Block for up to 2 seconds or until the stream has a new entry.
        # * If the stream has no new entries (XREAD returns null or
        #   an empty result list):
        #     * Increment retryCount
        # * If the stream has new entries:
        #     * Set retryCount to 0
        #     * Log the location and temperature values read from the stream
        #       (stored in fields "location" and "tempF")
        #
        # redis-py xread() method expects a dictionary with the stream name
        # mapped to the last entry ID of this stream as it can read from
        # multiple streams at once.
        #
        # The return value of xread() is an array of streams.
        #
        # see https://redis-py.readthedocs.io/en/stable/#redis.Redis.xread

        try:
            results = cls.redis.xread({STREAM_NAME: last_entry_id}, count=1, block=2000)
            return results
        except ResponseError as inst:
            print(f"Stream name: {STREAM_NAME}")
            print(type(inst))
            print(inst)
            return None

    @classmethod
    def consumer(cls):
        """
        Reads entries from a stream, blocking for up to
        2 seconds each time it accesses the stream.  If
        the stream has no new entries 5 consecutive times,
        the consumer stops trying and returns.
        """
        print('Starting consumer.')

        retry_count = 0

        last_entry_id = '0-0'

        while retry_count < 5:
            results = cls.read_stream(last_entry_id)

            if not results:
                print('Stream has no new entries.')
                retry_count += 1
            else:
                # Get the first entry returned for the first stream read.
                entry = results[0][1][0]
                json_formatted_str = json.dumps(entry, indent=2)
                print(f"New user: {json_formatted_str}")

                # Store the ID of this entry to use in the next XREAD call.
                last_entry_id = entry[0]

                # Reset the retry count.
                retry_count = 0

        print('Consumer shutting down.')

    @classmethod
    def usage(cls):
        print('Usage: NewUserService consumer')

    @classmethod
    def run_lab(cls, args):
        if len(args) == 2:
            if args[1] == 'consumer':
                cls.consumer()
            else:
                cls.usage()
        else:
            cls.usage()


if __name__ == '__main__':
    NewUserService().run_lab(sys.argv)
