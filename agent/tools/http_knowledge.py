from typing import Optional
from bs4 import BeautifulSoup
import httpx
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
from langchain.tools import tool
from pydantic import Field

class HTTPKnowledgeSource(BaseKnowledgeSource):
    url: str = Field(description="The URL to fetch")

    def validate_content(self):
        return super().validate_content()
    
    def load_content(self) -> str:
        """
        Fetches a webpage and returns its text content.
        
        Args:
            timeout (int, optional): Request timeout in seconds. Defaults to 10.
            
        Returns:
            str: The extracted text content from the webpage
        """
        try:
            # Configure httpx client with timeout and following redirects
            client = httpx.Client(
                # timeout=timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )
            
            # Fetch the page
            response = client.get(self.url)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Extract text content
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text (remove excessive newlines and spaces)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return f"""
            Content from {self.url}:
            
            {text}
            """
            
        except httpx.HTTPError as e:
            return f"Error fetching webpage: {str(e)}"
        except Exception as e:
            return f"Error processing webpage: {str(e)}"
        finally:
            client.close()

    def add(self) -> None:
        content = self.load_content()
        chunks = self._chunk_text(content)
        self.chunks.extend(chunks)

        self._save_documents()

    # def validate_content(self) -> bool:
    #     return True
      