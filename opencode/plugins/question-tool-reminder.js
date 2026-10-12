const TARGET_AGENTS = new Set(["plan"]);
const MAX_SESSIONS = 100;
const REMINDER =
  "When you need input from the user — clarifying questions, choices between options, or open questions at the end of a plan — use the `question` tool rather than listing questions in your response; batch related questions into one call with concrete options, recommended option first.";

export const QuestionToolReminderPlugin = async () => {
  const agentsBySession = new Map();

  return {
    "chat.message": async (input) => {
      if (typeof input?.agent !== "string" || typeof input.sessionID !== "string") return;

      agentsBySession.set(input.sessionID, input.agent);
      while (agentsBySession.size > MAX_SESSIONS) {
        agentsBySession.delete(agentsBySession.keys().next().value);
      }
    },

    "experimental.chat.system.transform": async (input, output) => {
      if (!TARGET_AGENTS.has(agentsBySession.get(input?.sessionID))) return;
      if (!output || !Array.isArray(output.system)) return;
      if (output.system.includes(REMINDER)) return;

      output.system.push(REMINDER);
    },
  };
};

export default QuestionToolReminderPlugin;
