// app/api/copilotkit/route.ts
import {
    CopilotRuntime,
    ExperimentalEmptyAdapter,
    copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();
const agentUrl = (
    process.env.LANGGRAPH_URL ||
    process.env.NEXT_PUBLIC_AGENT_URL ||
    "http://localhost:8223"
).replace(/\/+$/, "");

const runtime = new CopilotRuntime({
    agents: {
        praxis: new LangGraphHttpAgent({
            url: agentUrl,
        }),
        upskill: new LangGraphHttpAgent({
            url: agentUrl,
        }),
    },
});

export const GET = async () => {
    return Response.json({
        status: "ok",
        agentUrl,
        agents: ["praxis", "upskill"],
    });
};

export const POST = async (req: NextRequest) => {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
        runtime,
        serviceAdapter,
        endpoint: "/api/copilotkit",
    });
    return handleRequest(req);
};
