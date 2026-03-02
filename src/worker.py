import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional, Union

from .storage import RedisStorage
from .memory_storage import MemoryStorage
from .event_processor import EventProcessor
from .models import UserEvent
from .config import config
from .exceptions import RedisConnectionError, ProcessingError


class EventWorker:
    """Background worker for processing events from the queue"""
    
    def __init__(self, storage: Union[RedisStorage, MemoryStorage]):
        self.storage = storage
        self.processor = EventProcessor(storage, config.processing)
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info("Received shutdown signal")
        self.running = False
    
    async def start(self, batch_size: int = 10, poll_interval: float = 1.0):
        """Start the worker to process events"""
        self.running = True
        self.logger.info("Starting event worker...")
        
        processed_count = 0
        
        while self.running:
            try:
                # Process events in batches for efficiency
                batch_processed = await self._process_event_batch(batch_size)
                processed_count += batch_processed
                
                if batch_processed > 0:
                    self.logger.info(f"Processed {batch_processed} events (total: {processed_count})")
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
        
        self.logger.info(f"Worker stopped. Total events processed: {processed_count}")
    
    async def _process_event_batch(self, batch_size: int) -> int:
        """Process a batch of events"""
        processed = 0
        
        for _ in range(batch_size):
            event = self.storage.dequeue_event()
            if not event:
                break
                
            try:
                self.processor.process_event(event)
                processed += 1
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
        
        return processed
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        return {
            "running": self.running,
            "queue_size": self.storage.get_queue_size(),
            "timestamp": datetime.now().isoformat()
        }


def start_worker():
    """Entry point to start the worker"""
    logging.basicConfig(
        level=getattr(logging, config.server.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Initialize storage with config
    try:
        storage = RedisStorage(config.redis)
        logger.info("Worker using Redis storage")
    except RedisConnectionError:
        logger.warning("Redis not available, using in-memory storage")
        storage = MemoryStorage(config.processing)
    
    worker = EventWorker(storage)
    
    # Run the worker
    try:
        asyncio.run(worker.start(
            batch_size=config.processing.batch_size,
            poll_interval=config.processing.poll_interval
        ))
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")


if __name__ == "__main__":
    start_worker()