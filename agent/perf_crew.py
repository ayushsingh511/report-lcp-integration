from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeWebsiteTool, WebsiteSearchTool
from langchain_openai import ChatOpenAI
from tools.http_knowledge import HTTPKnowledgeSource
import os
from crewai.memory import ShortTermMemory
from crewai.memory.storage.rag_storage import RAGStorage
from tools.lcp_filter_tool import LCPFilterTool

src = HTTPKnowledgeSource(url="https://www.aem.live/developer/keeping-it-100")

@CrewBase
class PerfCrew:
    """Web Performance Crew"""

    llm = ChatOpenAI(model="azure/gpt-4o")

    embedder_config = {
        "provider": "azure",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": os.getenv("AZURE_API_KEY"),
            "api_base": os.getenv("AZURE_API_BASE"),
            "api_type": "azure",
            "api_version": os.getenv("AZURE_API_VERSION"),
        },
    }

    @agent 
    def knowledge_gathering_agent(self) -> Agent:
        return Agent(
            role=self.agents_config["knowledge_gathering_agent"]["role"],
            goal=self.agents_config["knowledge_gathering_agent"]["goal"],
            backstory=self.agents_config["knowledge_gathering_agent"]["backstory"],
            llm=self.llm,
            knowledge_sources=[src],
            embedder_config=self.embedder_config
        )

    @agent
    def perf_analysis_agent(self) -> Agent:
        return Agent(
            role=self.agents_config["perf_analysis_agent"]["role"],
            goal=self.agents_config["perf_analysis_agent"]["goal"],
            backstory=self.agents_config["perf_analysis_agent"]["backstory"],
            llm=self.llm
            # tools=[LCPFilterTool().filter_lcp_data]
        )
    
    @task
    def gather_knowledge_task(self) -> Task:
        return Task(
            config=self.tasks_config["gather_knowledge_task"],
        )

    @task
    def lcp_perf_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["lcp_perf_analysis_task"],
        )
    
    @task
    def lcp_perf_analysis_task_review(self) -> Task:
        return Task(
            config=self.tasks_config["lcp_perf_analysis_task_review"],
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Web Performance Crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            # manager_agent=self.manager_agent,
            # manager_llm=self.llm,
            # process=Process.hierarchical,
            verbose=True,
            # planning=True,
            # planning_llm=self.llm,
            embedder=self.embedder_config,
            short_term_memory=ShortTermMemory(
                storage=RAGStorage(type="short_term", embedder_config=self.embedder_config),
            ),
        )
