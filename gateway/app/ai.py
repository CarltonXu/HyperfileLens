"""
AI query functionality
Supports placeholder implementation and can be extended to real LLM
"""
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from .config import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract AI provider interface"""
    
    @abstractmethod
    async def query(self, question: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute AI query with context"""
        pass


class PlaceholderAIProvider(AIProvider):
    """Placeholder AI provider for basic file matching"""
    
    async def query(self, question: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple keyword-based matching"""
        question_lower = question.lower()
        
        # Extract keywords from question
        keywords = question_lower.split()
        
        # Score each file based on keyword matches
        scored_files = []
        for file_info in context:
            score = 0
            name_lower = file_info.get("name", "").lower()
            path_lower = file_info.get("path", "").lower()
            
            for keyword in keywords:
                if keyword in name_lower:
                    score += 2
                if keyword in path_lower:
                    score += 1
            
            if score > 0:
                scored_files.append({
                    **file_info,
                    "relevance_score": score
                })
        
        # Sort by relevance
        scored_files.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Generate response
        if scored_files:
            top_files = scored_files[:10]
            response = f"Found {len(scored_files)} files matching your query.\n\n"
            response += "Top matches:\n"
            for i, f in enumerate(top_files, 1):
                response += f"{i}. {f['name']} ({f['path']})\n"
        else:
            response = "No files found matching your query."
        
        return {
            "response": response,
            "matched_files": scored_files[:10],
            "total_matches": len(scored_files),
            "provider": "placeholder"
        }


class OpenAIProvider(AIProvider):
    """OpenAI API provider"""
    
    def __init__(self, api_key: str, api_url: Optional[str] = None):
        self.api_key = api_key
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
    
    async def query(self, question: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Query OpenAI API"""
        try:
            import httpx
            
            # Build context string
            context_str = "\n".join([
                f"- {f['name']} at {f['path']} ({f.get('size', 0)} bytes)"
                for f in context[:50]  # Limit context
            ])
            
            prompt = f"""You are a helpful assistant for a backup file system.
Users can ask questions about their backed up files.

Available files (showing top 50):
{context_str}

User question: {question}

Please provide a helpful response about the files that might be relevant to the user's question."""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": "You are a helpful backup file assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "response": data["choices"][0]["message"]["content"],
                        "matched_files": context[:10],
                        "total_matches": len(context),
                        "provider": "openai"
                    }
                else:
                    logger.error(f"OpenAI API error: {response.status_code}")
                    return {
                        "response": "Sorry, I couldn't process your request.",
                        "error": True,
                        "provider": "openai"
                    }
        except Exception as e:
            logger.error(f"OpenAI query error: {e}")
            return {
                "response": f"Error: {str(e)}",
                "error": True,
                "provider": "openai"
            }


class AIQueryEngine:
    """AI Query Engine that routes to appropriate provider"""
    
    def __init__(self):
        self.provider: AIProvider = self._create_provider()
    
    def _create_provider(self) -> AIProvider:
        """Create AI provider based on configuration"""
        provider_type = settings.AI_PROVIDER.lower()
        
        if provider_type == "openai" and settings.AI_API_KEY:
            return OpenAIProvider(
                api_key=settings.AI_API_KEY,
                api_url=settings.AI_API_URL
            )
        else:
            return PlaceholderAIProvider()
    
    async def query(
        self,
        question: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute AI query"""
        if not settings.AI_ENABLED:
            return {
                "response": "AI query is disabled.",
                "error": True,
                "provider": "disabled"
            }
        
        return await self.provider.query(question, files)
    
    async def suggest_restore(
        self,
        question: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Suggest files to restore based on question"""
        result = await self.query(question, files)
        
        suggestions = result.get("matched_files", [])
        
        return {
            "suggestions": [
                {
                    "path": f["path"],
                    "name": f["name"],
                    "reason": f"Matched with relevance score: {f.get('relevance_score', 0)}"
                }
                for f in suggestions[:5]
            ],
            "response": result.get("response", ""),
            "provider": result.get("provider", "unknown")
        }


# Global instance
ai_engine = AIQueryEngine()
