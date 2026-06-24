from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

contextualize_question_prompt = ChatPromptTemplate.from_messages([
  ("system", (
    "Given a conversational history and the most recent user query, rewrite the query as a standalone question"
    "that makes sense without relying on the previous context. Do not provide an answer - only reformulate the question"
    "if necessary; otherwise, return it unchanged."
  )),
  MessagesPlaceholder("chat_history"),
  ("human", "{input}"),
])

#Prompt for answering based on context
context_qa_prompt = ChatPromptTemplate.from_messages([
  ("system", (
    "You are an assistant for answering questions based on provided context. Use only the following retrieved "
    "information to answer the question. If the answer is not found in the context, say you don't know. Always use all the "
    "relevant information provided, and never make up information that is not included in the retrieved context. Keep"
    " your answer concise and to the point.\n\n{context}"
  )),
  MessagesPlaceholder("chat_history"),
  ("human", "{input}"),
])

#Central dictionary to register prompts
PROMPT_REGISTRY = {
    "contextualize_question": contextualize_question_prompt,
    "context_qa": context_qa_prompt
}
