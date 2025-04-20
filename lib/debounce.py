import asyncio
import functools

def debounce_async(delay_seconds: float = 0.5):
    def decorator(func):
        task_name = f"_{func.__name__}_debounce_task"

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Cancel any existing debounce task
            existing_task = getattr(self, task_name, None)
            if existing_task:
                existing_task.cancel()

            # Create a new task that will execute after the delay
            async def debounced():
                try:
                    await asyncio.sleep(delay_seconds)
                    await func(self, *args, **kwargs)
                except asyncio.CancelledError:
                    pass

            setattr(self, task_name, asyncio.create_task(debounced()))

        return wrapper
    return decorator
