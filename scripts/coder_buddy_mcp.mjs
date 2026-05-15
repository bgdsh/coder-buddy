#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const buddyIp = process.env.BUDDY_IP || '192.168.31.219';
const baseUrl = (process.env.BUDDY_URL || `http://${buddyIp}`).replace(/\/$/, '');
const timeoutMs = Number(process.env.BUDDY_TIMEOUT_MS || 5000);

function statusResult(status) {
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(status, null, 2),
      },
    ],
    structuredContent: status,
  };
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      signal: controller.signal,
    });
    const text = await response.text();
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${text}`);
    }
    try {
      return JSON.parse(text);
    } catch (error) {
      throw new Error(`Expected JSON response from ${path}: ${text}`);
    }
  } finally {
    clearTimeout(timer);
  }
}

async function post(path) {
  return request(path, { method: 'POST' });
}

async function setTrack(track) {
  const body = new URLSearchParams({ track }).toString();
  return request('/config/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
}

const tools = [
  {
    name: 'coder_buddy_trigger',
    description: 'Start or intensify a Coder Buddy attention alert. Maps to POST /trigger.',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
    },
  },
  {
    name: 'coder_buddy_stop',
    description: 'Decrement the Coder Buddy alert level. Maps to POST /stop.',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
    },
  },
  {
    name: 'coder_buddy_reset',
    description: 'Clear the Coder Buddy alert state. Maps to POST /reset.',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
    },
  },
  {
    name: 'coder_buddy_status',
    description: 'Read Coder Buddy device status. Maps to GET /status.',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
    },
  },
  {
    name: 'coder_buddy_set_track',
    description: 'Set the WAV track used for future alerts. Maps to POST /config/track.',
    inputSchema: {
      type: 'object',
      properties: {
        track: {
          type: 'string',
          description: 'WAV filename from the device track list, for example approve_soft.wav.',
        },
      },
      required: ['track'],
      additionalProperties: false,
    },
  },
];

const server = new Server(
  {
    name: 'coder-buddy-esp32',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

server.setRequestHandler(CallToolRequestSchema, async (requestMessage) => {
  const { name, arguments: args = {} } = requestMessage.params;
  try {
    if (name === 'coder_buddy_trigger') {
      return statusResult(await post('/trigger'));
    }
    if (name === 'coder_buddy_stop') {
      return statusResult(await post('/stop'));
    }
    if (name === 'coder_buddy_reset') {
      return statusResult(await post('/reset'));
    }
    if (name === 'coder_buddy_status') {
      return statusResult(await request('/status'));
    }
    if (name === 'coder_buddy_set_track') {
      if (!args.track || typeof args.track !== 'string') {
        throw new Error('coder_buddy_set_track requires a string track argument');
      }
      return statusResult(await setTrack(args.track));
    }
    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    return {
      isError: true,
      content: [
        {
          type: 'text',
          text: error instanceof Error ? error.message : String(error),
        },
      ],
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
