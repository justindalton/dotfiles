const TARGET_AGENTS = new Set(["plan"]);
const REMINDER =
  "When you need input from the user — clarifying questions, choices between options, or open questions at the end of a plan — use the `question` tool rather than listing questions in your response; batch related questions into one call with concrete options, recommended option first.";

export default {
  id: "dotfiles.question-tool-reminder",
  async setup(ctx) {
    await ctx.session.hook("context", (event) => {
      if (!TARGET_AGENTS.has(event.agent)) return;
      if (event.system.some((part) => part.type === "text" && part.text === REMINDER)) return;

      event.system.push({ type: "text", text: REMINDER });
    });
  },
};
