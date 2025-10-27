import asyncio
import io
import json
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from openai import OpenAI
from tqdm import tqdm
import concurrent
from openai import OpenAI, RateLimitError, APITimeoutError
import time
import base64
from pydantic import BaseModel
from enum import Enum


def init_model(model: str, api_key: str, temperature: float = 1):
    model_client = OpenAIChatCompletionClient(
        model=model, api_key=api_key, temperature=temperature
    )
    question_answering_agent = AssistantAgent(
        name="question_answering_agent",
        model_client=model_client,
        system_message="""
        ** Context **
        You are a research assistant participating in a water resource management project called "Just Transitions".
        The project is about future scenarios for the Sacramento-San Joaquin Delta focused on salinity management and climate change adaptation. 
        This research aims to diversify public and stakeholder participation in considering and assessing future salinity management options for the Delta. 
        ** Task **
        You are tasked with answering public questions about the project. Answer the user's questions to the best of your ability.
        """,
    )
    return question_answering_agent


async def chat(messages: list, model: str, api_key: str, temperature: float = 1):
    agent = init_model(model=model, api_key=api_key, temperature=temperature)
    messages = messages_reformat(messages)
    response = await agent.on_messages(
        messages=messages,
        cancellation_token=CancellationToken(),
    )
    response = response.chat_message.content
    messages = add_message(response, "assistant", messages)
    messages = [m.model_dump(mode="json") for m in messages]
    return response, messages


def messages_reformat(messages: list):
    return [
        TextMessage(content=message["content"], source=message["source"])
        for message in messages
    ]


def add_message(message: str, source: str, messages: list[TextMessage]):
    messages.append(TextMessage(content=message, source=source))
    return messages


# Function to encode the image
def encode_image(image):
    return base64.b64encode(image.read()).decode("utf-8")


class ClassificationEnum(Enum):
    IMPACTS_SALINITY = "impacts salinity"
    IMPACTED_BY_SALINITY = "impacted by salinity"
    N_A = "N/A"

    def __str__(self):
        return self.value


class Transcription(BaseModel):
    node_label: str
    classification: ClassificationEnum

    def to_obj(self):
        return {
            "node_label": self.node_label,
            "classification": str(self.classification.value),
        }


class TranscriptionResponse(BaseModel):
    response: list[Transcription]

    def parsed(self):
        return [r.to_obj() for r in self.response]


def transcribe_mental_model(image_data, api_key: str = None) -> str:
    """
    Sends a hand-drawn mental model image to OpenAI's Vision API and returns a bullet list of nodes.

    Parameters:
        image_path (str): Path to the image file.
        api_key (str): Your OpenAI API key. If None, it uses the key from the environment variable.

    Returns:
        str: A bullet list of nodes from the mental model.
    """

    # Use environment variable if no API key provided
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError(
                "OpenAI API key not provided and OPENAI_API_KEY environment variable not set"
            )

    # Read and encode the image as base64
    # base64_image = encode_image(image)
    # header, encoded = image_data.split(',', 1)
    # base64_image = base64.b64decode(encoded)
    header, encoded = image_data.split(",", 1)
    binary_data = base64.b64decode(encoded)

    # Create a file-like object from binary data
    image_stream = io.BytesIO(binary_data)
    base64_image = encode_image(image_stream)

    client = OpenAI(api_key=api_key)
    # Prepare the message to GPT-4 with Vision
    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": "You are a helpful assistant that extracts node labels from visual mental models.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": """
                                Please transcribe the node labels in this hand-drawn mental model diagram. 
                                The mental model represents factors impacting salinity or impacted by salinity. 
                                Output a clean list of the node labels separated by semicolon, no extra commentary. 
                                Additionally, for each factor (that is not Salinity), classify it as either 'impacts salinity' or 'impacted by salinity' 
                                If it is Salinity, classify it as 'N/A'.
                                based on the relationships shown in the image.
                            """,
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}",
                    },
                ],
            },
        ],
        temperature=0,
        text_format=TranscriptionResponse,
    )

    return response.output_parsed.parsed()


def multithread_code_classification(nodes, codebook, api_key):
    """
    Classifies the given code using the provided codebook.

    Parameters:
        codes list(str): The code to classify.
        codebook (dict): A dictionary mapping codes to their classifications.

    Returns:
        str: The classification of the code.
    """
    code_book_str = json.dumps(codebook, ensure_ascii=False)

    def prompt_factory(code_book_str, node):
        return [
            {
                "role": "system",
                "content": """You are a research assistant. You are given a codebook, and the user will give you a label. Your task is to classify the label according to the codebook.
            Here is the codebook:
            {code_book_str}
            Reply with the codes that best match the label. Do not return an empty list.
            Reply with the following JSON format:
            {{
                "matched_codes": str[]
            }}
            """.format(
                    code_book_str=code_book_str
                ),
            },
            {"role": "user", "content": "label: {node}".format(node=node)},
        ]

    client = OpenAI(api_key=api_key)
    prompts = [prompt_factory(code_book_str, node) for node in nodes]
    responses = multithread_prompts(
        client, prompts, model="gpt-4o-mini", temperature=0.0, response_format="json"
    )
    # response = client.responses.create(
    #     model="gpt-4o",
    #     input=prompts,
    #     text={"format": {"type": "json_object"}},
    # )
    return responses


def multithread_prompts(
    client,
    prompts,
    model="gpt-4o-mini",
    temperature=0.5,
    response_format=None,
    seed=None,
):
    l = len(prompts)
    # results = np.zeros(l)
    with tqdm(total=l) as pbar:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=100)
        futures = [
            executor.submit(
                request_gpt, client, prompt, model, temperature, response_format, seed
            )
            for prompt in prompts
        ]
        for _ in concurrent.futures.as_completed(futures):
            pbar.update(1)
    concurrent.futures.wait(futures)
    return [future.result() for future in futures]


def request_gpt(
    client, messages, model="gpt-4o-mini", temperature=0.5, format=None, seed=None
):
    with open("request_log.txt", "a", encoding="utf-8") as f:
        f.write(f"model: {model}, temperature: {temperature}, format: {format}\n")
        f.write(json.dumps(messages, ensure_ascii=False) + "\n")
        f.write("=====================================\n")
    try:
        if format == "json":
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
                seed=seed,
            )

            try:
                json.loads(response.choices[0].message.content)
                return response.choices[0].message.content
            except json.JSONDecodeError as e:
                print("JSON Decode Error")
                print(e)
                time.sleep(5)
                return request_gpt(
                    client, messages, model, temperature=1.0, format=format
                )

        else:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, seed=seed
            )
        return response.choices[0].message.content
    except RateLimitError as e:
        print("RateLimitError")
        print(e)
        time.sleep(5)
        return request_gpt(client, messages, model, temperature, format)
    except APITimeoutError as e:
        print("APITimeoutError")
        print(messages)
        time.sleep(5)
        return request_gpt(client, messages, model, temperature, format)


async def main() -> None:
    model = "gpt-4o-mini"
    api_key = open("../api_key").read().strip()
    agent = init_model(model, api_key)
    messages = [{"content": "Introduce me to the project.", "source": "user"}]
    messages = messages_reformat(messages)
    response, messages = await chat(agent, messages)
    print(response)
    print(messages)


if __name__ == "__main__":
    asyncio.run(main())
