import type { PromptRole } from "@/lib/api"

export interface PromptTemplateSection {
  heading: string
  guidance: string
  example: string
}

export interface PromptTemplate {
  title: string
  summary: string
  sections: PromptTemplateSection[]
}

// A researched, role-specific template for writing effective LLM prompts.
// Shown in the UI's guidance panel, contextual to the Prompt's role.
export const PROMPT_TEMPLATES: Record<PromptRole, PromptTemplate> = {
  system: {
    title: "System prompt",
    summary:
      "Sets who the model is and the rules it operates under. Keep it lean — put detailed task instructions in the user prompt instead.",
    sections: [
      {
        heading: "Identity",
        guidance: "State who the model is, in one line.",
        example: "You are a senior customer support agent for Acme Corp.",
      },
      {
        heading: "Success criteria",
        guidance: "List what a good response looks like, as bullet points.",
        example:
          "- Resolves the customer's issue in the first reply when possible\n- Escalates only when policy requires it",
      },
      {
        heading: "Constraints",
        guidance: "State hard rules — things the model must never do.",
        example:
          "- Never promise a refund without checking order status\n- Never reveal internal tooling names",
      },
      {
        heading: "Output format",
        guidance: "Specify the exact shape of the response.",
        example: "Respond in 2-4 sentences, plain text, no markdown headers.",
      },
      {
        heading: "Edge cases",
        guidance: "Say what to do when input is ambiguous or missing.",
        example: "If the customer's order number is missing, ask for it before proceeding.",
      },
      {
        heading: "Examples",
        guidance: "Give 1-3 short example exchanges, wrapped in tags.",
        example: "<example>\nCustomer: My order hasn't arrived.\nResponse: ...\n</example>",
      },
    ],
  },
  user: {
    title: "User prompt",
    summary:
      "Delivers the specific request — most of the task detail belongs here, not in the system prompt.",
    sections: [
      {
        heading: "Instructions",
        guidance: "State the specific ask in the opening line.",
        example: "Summarize the attached support ticket in 3 bullet points.",
      },
      {
        heading: "Context",
        guidance:
          "Wrap background material in XML-ish tags so it reads as data, not instructions.",
        example: "<ticket>\n{{ ticket_text }}\n</ticket>",
      },
      {
        heading: "Task",
        guidance: "Restate precisely what output is needed, especially if it's more specific than Instructions.",
        example: "Identify the customer's core complaint and any action they've requested.",
      },
      {
        heading: "Output format",
        guidance: "Pin down structure, length, and format expectations.",
        example: "Return exactly 3 bullet points, no preamble.",
      },
    ],
  },
  assistant: {
    title: "Assistant prompt",
    summary:
      "Either a prefill that forces the start of the model's own reply, or a canned exemplar turn used to steer style in a few-shot template.",
    sections: [
      {
        heading: "Prefill",
        guidance:
          "Start the assistant's reply yourself to force a format, e.g. the opening of a JSON object.",
        example: '{\n  "complaint": "',
      },
      {
        heading: "Exemplar turn",
        guidance:
          "A canned \"ideal\" reply used in a few-shot template to steer tone and style for later turns.",
        example: "Thanks for reaching out — I've checked your order and it shipped yesterday.",
      },
    ],
  },
}
