import { definePluginEntry, type AnyAgentTool, type OpenClawPluginApi } from "./api.js";
import {
  createMainWorkerTool,
  createRunOnceTool,
  createRunLoopTool,
  createHeartbeatTool,
  createExportCoreSubmissionsTool,
  createProcessTaskFileTool,
} from "./src/tools.js";

export default definePluginEntry({
  id: "mine",
  name: "Mine",
  description: "Runs mine/social-data-crawler jobs from OpenClaw tools and worker triggers.",
  register(api: OpenClawPluginApi) {
    api.registerTool(createMainWorkerTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createHeartbeatTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createRunOnceTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createRunLoopTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createProcessTaskFileTool(api) as unknown as AnyAgentTool, { optional: true });
    api.registerTool(createExportCoreSubmissionsTool(api) as unknown as AnyAgentTool, {
      optional: true,
    });
  },
});
