
from core.agent_base import Agent, AgentConfig
import asyncio

class MoonBagAgent(Agent):
    def __init__(self):
        super().__init__(AgentConfig(
            name="moon_bag_agent",
            version="1.0.0",
            description="MOON BAG ACTIVATED — Buying PEPE"
        ))
    
    async def run(self):
        self.logger.info("MOON BAG ACTIVATED — Buying PEPE")
        while not self._shutdown_event.is_set():
            await asyncio.sleep(60)
