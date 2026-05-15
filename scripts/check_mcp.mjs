#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const buddyIp = process.env.BUDDY_IP || '192.168.31.219';

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ['coder_buddy_mcp.mjs'],
  env: { ...process.env, BUDDY_IP: buddyIp },
});

const client = new Client(
  {
    name: 'coder-buddy-check',
    version: '1.0.0',
  },
  {
    capabilities: {},
  }
);

try {
  await client.connect(transport);

  const listed = await client.listTools();
  const names = listed.tools.map((tool) => tool.name);
  for (const name of ['coder_buddy_trigger', 'coder_buddy_stop', 'coder_buddy_reset', 'coder_buddy_status', 'coder_buddy_set_track']) {
    if (!names.includes(name)) {
      throw new Error(`Missing MCP tool: ${name}`);
    }
  }

  const status = await client.callTool({ name: 'coder_buddy_status', arguments: {} });
  const payload = JSON.parse(status.content[0].text);
  if (payload.ip !== buddyIp || typeof payload.level !== 'number' || !Array.isArray(payload.tracks)) {
    throw new Error(`Unexpected status payload: ${JSON.stringify(payload)}`);
  }

  console.log(`MCP OK: ${names.length} tools, ${payload.device} at ${payload.ip}, level ${payload.level}`);
} finally {
  await client.close();
}
