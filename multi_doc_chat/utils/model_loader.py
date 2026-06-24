# """Python classes (usually inheriting from BaseModel) that define the structure, types, validation rules, and serialization behavior of your data. Their main purpose is to ensure that data entering your application is valid and has the expected format."""
# import os
# import sys
# import json
# from dotenv import load_dotenv
# from langchain_ollama import ChatOllama
# from multi_doc_chat.utils.config_loader import load_config
# from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
# from langchain_groq import ChatGroq
# from multi_doc_chat.logger.custom_logger import CustomLogger
# from multi_doc_chat.exception.custom_exception import DocumentPortalException

# from langchain_huggingface import HuggingFaceEmbeddings

# log = CustomLogger().get_logger(__name__)

# class ApiKeyManager:
#     REQUIRED_KEYS = ["GROQ_API_KEY", "GOOGLE_API_KEY"]

#     def __init__(self):
#         self.api_keys = {}
#         raw = os.getenv("API_KEYS")
        
#         if raw:
#             try:
#                 parsed = json.loads(raw)
#                 if not isinstance(parsed, dict):
#                     raise ValueError("API_KEYS is not a valid JSON object.")
#                 self.api_keys = parsed
#                 log.info("Loaded API keys from ECS secret")
#             except Exception as e:
#                 log.warning("Failed to parse API_KEYS as JSON", error=str(e))
        
#         #Fallback to individual env vars
#         for key in self.REQUIRED_KEYS:
#             if not self.api_keys.get(key):
#                 env_val = os.getenv(key)
#                 if env_val:
#                     self.api_keys[key] = env_val
#                     log.info(f"Loaded {key} from individual environment variable")
#         #Final check
#         missing = [k for k in self.REQUIRED_KEYS if not self.api_keys.get(k)]
#         if missing:
#             log.error("Missing required API keys", missing_keys=missing)
#             raise DocumentPortalException(f"Missing API keys:", sys)
        
#         log.info("API keys loaded", keys={k: v[:6] + "..." for k, v in self.api_keys.items()})
    
#     def get(self, key: str)->str:
#         val = self.api_keys.get(key)
#         if not val:
#             raise KeyError(f"API key for {key} is missing")
#         return val


# class ModelLoader:
#     """
#     Loads embedding models and LLMs based on config and environment.
#     """

#     def __init__(self):
#         if os.getenv("ENV", "local").lower() != "production":
#             load_dotenv()
#             log.info("Running in LOCAL mode: .env loaded")
#         else:
#             log.info("Running in PRODUCTION mode")

#         self.api_key_mgr = ApiKeyManager()
#         self.config = load_config()

#         log.info(
#             "YAML config loaded",
#             config_keys=list(self.config.keys())
#         )

#     def load_embeddings(self):
#         """
#         Load and return embedding model from Google Generative AI.
#         """

#         try:
#             model_name = self.config["embedding_model"]["model_name"]

#             log.info(
#                 "Loading embedding model",
#                 model=model_name
#             )

#             return GoogleGenerativeAIEmbeddings(
#                 model=model_name,
#                 google_api_key=self.api_key_mgr.get("GOOGLE_API_KEY")
#             )  # type: ignore

#         except Exception as e:
#             log.error(
#                 "Error loading embedding model",
#                 error=str(e)
#             )
#             raise DocumentPortalException("Failed to load embedding model", sys)
        
#     def load_llm(self):
#         """
#         Load and return the configured LLM model.
#         """
#         llm_block = self.config["llm"]
#         provider_key = os.getenv(
#             "LLM_PROVIDER",
#             llm_block.get("active", "ollama")
#         )
#         if provider_key not in llm_block:
#             log.error(
#                 "LLM provider not found in config",
#                 provider=provider_key,
#                 available_providers=list(llm_block.keys())
#             )
#             raise ValueError(f"LLM provider '{provider_key}' not found in config")
#         llm_config = llm_block[provider_key]
#         provider = llm_config.get("provider")
#         model_name = llm_config.get("model_name")
#         temperature = llm_config.get("temperature", 0.2)
#         max_tokens = llm_config.get("max_tokens", 2048)

#         log.info("Loading LLM", provider=provider, model=model_name)

#         if provider == "google":
#             return ChatGoogleGenerativeAI(
#                 model=model_name,
#                 temperature=temperature,
#                 max_output_tokens=max_tokens,
#                 google_api_key=self.api_key_mgr.get("GOOGLE_API_KEY")
#             )
#         elif provider == "groq":
#             return ChatGroq(
#                 model=model_name,
#                 temperature=temperature,
#                 max_output_tokens=max_tokens,
#                 groq_api_key=self.api_key_mgr.get("GROQ_API_KEY")
#             )
#         elif provider == "ollama":
#             return ChatOllama(
#             model=model_name,
#             temperature=temperature
#             )

#         else:
#             log.error(
#                 "Unsupported LLM provider",
#                 provider=provider
#             )
#             raise ValueError(f"Unsupported LLM provider: {provider}")

# if __name__ == "__main__":
#     loader = ModelLoader()
#     #test embeddings
#     embeddings = loader.load_embeddings()
#     print(f"Embedding Model Loaded: {embeddings}")
#     result = embeddings.embed_query("Hello, how are you?")
#     print("Embedding Result:", result)

#     #test llm
#     llm = loader.load_llm()
#     print("LLM Model Loaded: {llm}")
#     result = llm.invoke("Hello, how are you?")
#     print("LLM Result:", result)        




"""
Model Loader

Loads:
1. Embedding Models
   - HuggingFace
   - Google Gemini Embeddings

2. LLM Providers
   - Ollama
   - Google Gemini
   - Groq

Configuration is read from config.yaml.
"""

import json
import os
import sys

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import (
    GoogleGenerativeAIEmbeddings,
    ChatGoogleGenerativeAI,
)
from langchain_groq import ChatGroq

from multi_doc_chat.utils.config_loader import load_config
from multi_doc_chat.logger.custom_logger import CustomLogger
from multi_doc_chat.exception.custom_exception import (
    DocumentPortalException,
)

log = CustomLogger().get_logger(__name__)


class ApiKeyManager:
    """
    Loads API keys from:
    1. API_KEYS JSON env variable
    2. Individual env variables

    Keys are optional and only required
    when a provider actually uses them.
    """

    def __init__(self):
        self.api_keys = {}

        raw = os.getenv("API_KEYS")

        if raw:
            try:
                parsed = json.loads(raw)

                if isinstance(parsed, dict):
                    self.api_keys.update(parsed)

                log.info(
                    "Loaded API keys from API_KEYS env variable"
                )

            except Exception as e:
                log.warning(
                    "Failed to parse API_KEYS",
                    error=str(e)
                )

        for key in [
            "GOOGLE_API_KEY",
            "GROQ_API_KEY",
        ]:
            value = os.getenv(key)

            if value:
                self.api_keys[key] = value

                log.info(
                    f"Loaded {key} from environment"
                )

        log.info(
            "API key manager initialized",
            available_keys=list(self.api_keys.keys())
        )

    def get(self, key: str) -> str:
        value = self.api_keys.get(key)

        if not value:
            raise KeyError(
                f"Missing required API key: {key}"
            )

        return value


class ModelLoader:
    """
    Loads embeddings and LLMs from config.yaml.
    """

    def __init__(self):
        try:
            if (
                os.getenv("ENV", "local").lower()
                != "production"
            ):
                load_dotenv()

                log.info(
                    "Running in LOCAL mode (.env loaded)"
                )
            else:
                log.info(
                    "Running in PRODUCTION mode"
                )

            self.api_key_mgr = ApiKeyManager()
            self.config = load_config()

            log.info(
                "YAML config loaded",
                config_keys=list(self.config.keys())
            )

        except Exception as e:
            log.error(
                "Failed to initialize ModelLoader",
                error=str(e)
            )

            raise DocumentPortalException(
                "Failed to initialize ModelLoader",
                sys
            )

    # --------------------------------------------------
    # EMBEDDINGS
    # --------------------------------------------------

    def load_embeddings(self):
        """
        Load embedding model from config.yaml
        """

        try:
            emb_config = self.config["embedding_model"]

            provider = emb_config["provider"]
            model_name = emb_config["model_name"]

            log.info(
                "Loading embedding model",
                provider=provider,
                model=model_name
            )

            if provider == "huggingface":
                return HuggingFaceEmbeddings(
                    model_name=model_name
                )

            elif provider == "google":
                return GoogleGenerativeAIEmbeddings(
                    model=model_name,
                    google_api_key=self.api_key_mgr.get(
                        "GOOGLE_API_KEY"
                    ),
                )

            else:
                raise ValueError(
                    f"Unsupported embedding provider: {provider}"
                )

        except Exception as e:
            log.error(
                "Failed to load embeddings",
                error=str(e)
            )

            raise DocumentPortalException(
                "Failed to load embedding model",
                sys
            )

    # --------------------------------------------------
    # LLM
    # --------------------------------------------------

    def load_llm(self):
        """
        Load LLM from config.yaml
        """

        try:
            llm_block = self.config["llm"]

            provider_key = os.getenv(
                "LLM_PROVIDER",
                llm_block.get("active", "ollama"),
            )

            if provider_key not in llm_block:
                raise ValueError(
                    f"LLM provider '{provider_key}' not found in config"
                )

            llm_config = llm_block[provider_key]

            provider = llm_config["provider"]
            model_name = llm_config["model_name"]

            temperature = llm_config.get(
                "temperature",
                0.0,
            )

            max_tokens = llm_config.get(
                "max_tokens",
                2048,
            )

            log.info(
                "Loading LLM",
                provider=provider,
                model=model_name,
            )

            # ----------------------------
            # Gemini
            # ----------------------------
            if provider == "google":
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    google_api_key=self.api_key_mgr.get(
                        "GOOGLE_API_KEY"
                    ),
                )

            # ----------------------------
            # Groq
            # ----------------------------
            elif provider == "groq":
                return ChatGroq(
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    groq_api_key=self.api_key_mgr.get(
                        "GROQ_API_KEY"
                    ),
                )

            # ----------------------------
            # Ollama
            # ----------------------------
            elif provider == "ollama":
                return ChatOllama(
                    model=model_name,
                    temperature=temperature,
                )

            else:
                raise ValueError(
                    f"Unsupported provider: {provider}"
                )

        except Exception as e:
            log.error(
                "Failed to load LLM",
                error=str(e)
            )

            raise DocumentPortalException(
                "Failed to load LLM",
                sys
            )


# ------------------------------------------------------
# TEST
# ------------------------------------------------------

if __name__ == "__main__":
    loader = ModelLoader()

    print("\n=== TESTING EMBEDDINGS ===")

    embeddings = loader.load_embeddings()

    print(f"Embedding Model Loaded: {embeddings}")

    vector = embeddings.embed_query(
        "Hello, how are you?"
    )

    print(
        f"Embedding dimension: {len(vector)}"
    )

    print("\n=== TESTING LLM ===")

    llm = loader.load_llm()

    print(f"LLM Loaded: {llm}")

    response = llm.invoke(
        "What is Agentic AI?"
    )

    print("\nResponse:")
    print(response)