import logging
import random
import string
import traceback
from telethon.events import NewMessage
from telethon.tl.types import Message
from app.userbot import state
from app.shared.redis_client import get_redis_connection
from app import config

logger = logging.getLogger("userbot.handlers")

def _gen_request_id(length=8):
    """Generate a random request ID"""
    logger.debug(f"Generating random request ID with length={length}")
    
    try:
        request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        logger.debug(f"Generated request ID: {request_id}")
        return request_id
    except Exception as e:
        logger.exception(f"Error generating request ID: {e}")
        # Fallback to a timestamp-based ID to ensure we can continue
        import time
        fallback_id = f"fallback_{int(time.time())}"
        logger.warning(f"Using fallback request ID: {fallback_id}")
        return fallback_id

def register_handlers(client):
    """
    Register message handlers for the Telethon client
    
    Args:
        client: Telethon client instance
    """
    logger.info("Registering Telethon message handlers")
    
    try:
        @client.on(NewMessage(outgoing=False, from_users='me'))
        async def handle_message_input(event: Message):
            """Handle incoming messages from the user"""
            # Extract key information for logging context
            user_id = getattr(event, 'sender_id', 'unknown')
            chat_id = getattr(event, 'chat_id', 'unknown')
            message_id = getattr(event, 'id', 'unknown')
            
            logger.debug(f"Received message: user_id={user_id}, chat_id={chat_id}, message_id={message_id}")
            
            try:
                text = event.raw_text.strip() if hasattr(event, "raw_text") else ""
                logger.debug(f"Message text (length={len(text)}): {text[:20]}{'...' if len(text) > 20 else ''}")
                
                # Check for pending state
                request_id = state.get_pending_state(user_id)
                logger.debug(f"Pending state for user {user_id}: {request_id}")

                # Handle prompt input if pending
                if request_id:
                    logger.info(f"Processing pending request: user_id={user_id}, request_id={request_id}")
                    
                    if text.lower() == '/cancel':
                        logger.info(f"User cancelled operation: user_id={user_id}, request_id={request_id}")
                        state.clear_pending_state(user_id)
                        await event.respond("❌ Operation cancelled.")
                        return

                    if not text or len(text) < 3:
                        logger.warning(f"Invalid prompt (too short): user_id={user_id}, length={len(text)}")
                        await event.respond("⚠️ Please provide a valid prompt (min 3 chars) or /cancel.")
                        return

                    # Store prompt, update state, clear pending, enqueue
                    logger.debug(f"Storing prompt and updating request: user_id={user_id}, request_id={request_id}")
                    state.store_request_data(request_id, {"custom_prompt": text, "status": "QUEUED"})
                    state.clear_pending_state(user_id)
                    
                    logger.info(f"Enqueueing job: user_id={user_id}, request_id={request_id}")
                    await enqueue_processing_job(event, user_id, request_id, custom_prompt=text)
                    
                    logger.debug(f"Sending confirmation: user_id={user_id}, request_id={request_id}")
                    msg = await event.respond("✅ Prompt received! The job is being queued.")
                    
                    logger.debug(f"Storing status message: user_id={user_id}, message_id={msg.id}")
                    state.set_status_message(user_id, event.chat_id, msg.id)
                    return

                # Not pending: specify target chat
                logger.debug(f"No pending request, processing chat specification: user_id={user_id}")
                
                if event.is_group or event.is_channel or event.fwd_from:
                    logger.debug(f"Processing group/channel/forward message: user_id={user_id}")
                    try:
                        if hasattr(event, "forward"):
                            logger.debug("Getting entity from forwarded message")
                            entity = await event.get_forwarded_from()
                        else:
                            logger.debug("Getting entity from current chat")
                            entity = await event.get_chat()
                            
                        chat_id = getattr(entity, "id", None) or event.chat_id
                        logger.info(f"Detected target chat: user_id={user_id}, chat_id={chat_id}")
                    except Exception as e:
                        logger.warning(f"Target chat parse fail: user_id={user_id}, error={e}")
                        await event.respond("❌ Could not detect chat. Forward a message or name the chat/channel.")
                        return
                elif text:
                    # Try resolve username or ID
                    logger.debug(f"Attempting to resolve chat from text: user_id={user_id}, text={text}")
                    try:
                        entity = await client.get_entity(text)
                        chat_id = entity.id
                        logger.info(f"Resolved chat: user_id={user_id}, chat_id={chat_id}, identifier={text}")
                    except Exception as e:
                        logger.warning(f"Failed to resolve chat: user_id={user_id}, identifier={text}, error={e}")
                        await event.respond("❌ Invalid chat username/ID. Try again, or forward a message.")
                        return
                else:
                    logger.warning(f"No chat specification provided: user_id={user_id}")
                    await event.respond("❌ Please forward a message or type a chat/channel username/ID.")
                    return

                # Ready: generate request_id, store state, prompt user for LLM prompt
                req_id = _gen_request_id()
                logger.info(f"Created new request: user_id={user_id}, request_id={req_id}, chat_id={chat_id}")
                
                logger.debug(f"Storing initial request data: request_id={req_id}")
                state.store_request_data(req_id, {
                    "target_chat_id": chat_id,
                    "status": "PENDING_PROMPT",
                    "user_id": user_id,
                })
                
                logger.debug(f"Setting pending prompt state: user_id={user_id}, request_id={req_id}")
                state.set_pending_prompt_state(user_id, req_id)
                
                logger.debug(f"Prompting user for custom prompt: user_id={user_id}")
                await event.respond("✏️ Now send me your summarization prompt for this chat (or /cancel).")
                
            except Exception as e:
                logger.exception(f"Error handling message: user_id={user_id}, error={e}")
                try:
                    await event.respond(f"❌ An error occurred: {str(e)[:100]}...")
                except Exception as respond_error:
                    logger.error(f"Failed to send error message: {respond_error}")
        
        logger.info("Successfully registered message handlers")
        return handle_message_input
    except Exception as e:
        logger.exception(f"Failed to register message handlers: {e}")
        raise

async def enqueue_processing_job(event, user_id, request_id, custom_prompt):
    """
    Enqueue a job for processing
    
    Args:
        event: Telethon message event
        user_id: User ID
        request_id: Request ID
        custom_prompt: User-provided prompt for LLM
    """
    logger.info(f"Enqueueing job: user_id={user_id}, request_id={request_id}")
    
    try:
        # Get Redis connection
        logger.debug("Getting Redis connection")
        redis_conn = get_redis_connection(config.settings)
        
        logger.debug("Getting RQ queue")
        queue = get_rq_queue(redis_conn, config.settings)
        
        # Get request data and chat_id
        logger.debug(f"Retrieving request data: request_id={request_id}")
        request_data = state.get_request_data(request_id)
        
        if not request_data:
            logger.error(f"Request data not found: request_id={request_id}")
            await event.respond("❌ Request data not found. Please try again.")
            return
            
        chat_id = request_data.get("target_chat_id")
        if not chat_id:
            logger.error(f"Target chat ID not found in request data: request_id={request_id}")
            await event.respond("❌ Target chat not specified. Please try again.")
            return
            
        logger.debug(f"Using session path: {config.settings.TELEGRAM_SESSION_PATH}")
        session_path = config.settings.TELEGRAM_SESSION_PATH

        # Enqueue job, update status, store rq_job_id
        logger.debug(f"Updating request status to QUEUED: request_id={request_id}")
        state.update_request_status(request_id, "QUEUED")
        
        # Create job metadata
        job_metadata = {
            'chat_id': chat_id, 
            'user_id': user_id, 
            'request_id': request_id
        }
        job_id = f"extract:{request_id}:{chat_id}"
        
        logger.debug(f"Enqueueing RQ job: job_id={job_id}, metadata={job_metadata}")
        job = queue.enqueue(
            "app.worker.tasks.extract_and_summarize_data",
            chat_id,
            session_path,
            user_id,
            request_id,
            custom_prompt,
            job_id=job_id,
            meta=job_metadata
        )
        
        if not job:
            logger.error(f"Failed to enqueue job: request_id={request_id}")
            await event.respond("❌ Failed to enqueue job. Please try again.")
            return
            
        logger.debug(f"Storing RQ job ID: request_id={request_id}, job_id={job.id}")
        state.add_rq_job_id(request_id, job.id)
        
        logger.info(f"Successfully enqueued job: user_id={user_id}, chat_id={chat_id}, job_id={job.id}")
    except Exception as e:
        logger.exception(f"Error enqueueing job: user_id={user_id}, request_id={request_id}, error={e}")
        try:
            await event.respond(f"❌ Failed to start processing: {str(e)[:100]}...")
        except Exception as respond_error:
            logger.error(f"Failed to send error message: {respond_error}")