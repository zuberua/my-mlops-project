#!/usr/bin/env python3
"""Generate AWS architecture diagram for the Mark Vle Strands Agent."""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.ml import Bedrock
from diagrams.aws.general import Users, GenericSDK
from diagrams.aws.devtools import Codebuild
from diagrams.aws.compute import ECS
from diagrams.programming.framework import Flask

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

with Diagram(
    "Mark Vle Strands Agent - Architecture",
    filename="mark-vle-architecture",
    show=False,
    direction="TB",
    graph_attr={"fontsize": "16", "bgcolor": "white", "pad": "0.8", "ranksep": "1.2"},
):
    engineer = Users("Engineers\n(Browser)")

    with Cluster("GitHub Actions CI/CD"):
        github = Codebuild("GitHub Actions\nBuild & Push")

    with Cluster("Amazon ECR"):
        ecr = ECS("Docker Image\n(ARM64)")

    with Cluster("Local Development"):
        flask = Flask("Flask App\nPort 5001")

    with Cluster("Amazon Bedrock AgentCore"):
        agentcore = Bedrock("AgentCore Runtime")

        with Cluster("Strands Agent"):
            agent = Bedrock("Mark Vle Agent\n(Strands SDK)")
            with Cluster("Agent Tools"):
                tools_search = GenericSDK("search_knowledge_base")
                tools_diagram = GenericSDK("generate_diagram")
                tools_xml = GenericSDK("export_xml")

    with Cluster("Amazon Bedrock - AI Models"):
        claude = Bedrock("litellm_proxy/\nbedrock-claude-sonnet-4.6\n(LLM)")
        titan = Bedrock("Titan Embed v2\n(Embeddings)")

    with Cluster("S3 Vector Bucket (CloudFormation)"):
        s3_vectors = S3("markvie-vectors-{acct}\n206 block embeddings")

    # User flows
    engineer >> Edge(label="HTTP", color="darkgreen") >> flask
    engineer >> Edge(label="API", color="darkgreen", style="dashed") >> agentcore

    # CI/CD flow
    github >> Edge(label="Docker push", color="purple") >> ecr
    ecr >> Edge(label="Deploy", color="purple") >> agentcore

    # Local dev to agent
    flask >> Edge(color="blue") >> agent

    # Agent to tools
    agent >> Edge(color="orange") >> tools_search
    agent >> Edge(color="orange") >> tools_diagram
    agent >> Edge(color="orange") >> tools_xml

    # AI model calls
    agent >> Edge(label="LLM", color="red") >> claude
    tools_search >> Edge(label="Embed query", color="red") >> titan

    # Data flow
    tools_search >> Edge(label="Cosine similarity\nsearch", color="blue") >> s3_vectors

print("Generated: mark-vle-architecture.png")
