import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getAgentServiceUrl() {
  const url = process.env.AGENT_SERVICE_URL;

  if (!url) {
    throw new Error("AGENT_SERVICE_URL is not configured.");
  }

  return url.replace(/\/$/, "");
}

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "";
}

async function parseAgentServiceResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

export async function GET(request: Request) {
  const requestId = crypto.randomUUID();

  try {
    const response = await fetch(`${getAgentServiceUrl()}/memory/list`, {
      method: "GET",
      headers: {
        "x-user-id": getUserId(request),
      },
      cache: "no-store",
    });

    const payload = await parseAgentServiceResponse(response);

    return NextResponse.json(
      {
        requestId,
        ...(typeof payload === "object" && payload !== null ? payload : {}),
      },
      { status: response.status },
    );
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        requestId,
        error:
          error instanceof Error
            ? error.message
            : "Failed to reach agent memory service.",
      },
      { status: 502 },
    );
  }
}