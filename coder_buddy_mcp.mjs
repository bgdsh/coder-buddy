#!/usr/bin/env node
const buddyIp = process.env.BUDDY_IP || '192.168.31.219';
const baseUrl = (process.env.BUDDY_URL || `http://${buddyIp}`).replace(/\/$/, '');
const timeoutMs = Number(process.env.BUDDY_TIMEOUT_MS || 5000);
let outputMode = 'content-length';

const tools = [
  {
    name: 'coder_buddy_trigger',
    description: 'Start or intensify a Coder Buddy attention alert. Maps to POST /trigger.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'coder_buddy_stop',
    description: 'Decrement the Coder Buddy alert level. Maps to POST /stop.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'coder_buddy_reset',
    description: 'Clear the Coder Buddy alert state. Maps to POST /reset.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'coder_buddy_status',
    description: 'Read Coder Buddy device status. Maps to GET /status.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
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

function writeMessage(message) {
  const body = JSON.stringify(message);
  if (outputMode === 'line') {
    process.stdout.write(`${body}\n`);
    return;
  }
  process.stdout.write(`Content-Length: ${Buffer.byteLength(body, 'utf8')}\r\n\r\n${body}`);
}

function respond(id, result) {
  writeMessage({ jsonrpc: '2.0', id, result });
}

function respondError(id, code, message) {
  writeMessage({ jsonrpc: '2.0', id, error: { code, message } });
}

function statusResult(status) {
  return {
    content: [{ type: 'text', text: JSON.stringify(status, null, 2) }],
    structuredContent: status,
  };
}

async function httpRequest(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${baseUrl}${path}`, { ...options, signal: controller.signal });
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
  return httpRequest(path, { method: 'POST' });
}

async function setTrack(track) {
  const body = new URLSearchParams({ track }).toString();
  return httpRequest('/config/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
}

async function callTool(name, args = {}) {
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
      return statusResult(await httpRequest('/status'));
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
      content: [{ type: 'text', text: error instanceof Error ? error.message : String(error) }],
    };
  }
}

async function handleRequest(message) {
  const hasId = Object.prototype.hasOwnProperty.call(message, 'id');
  if (!hasId) {
    return;
  }

  if (message.method === 'initialize') {
    respond(message.id, {
      protocolVersion: message.params?.protocolVersion || '2024-11-05',
      capabilities: { tools: {} },
      serverInfo: { name: 'coder-buddy-esp32', version: '1.0.0' },
    });
    return;
  }

  if (message.method === 'tools/list') {
    respond(message.id, { tools });
    return;
  }

  if (message.method === 'tools/call') {
    const { name, arguments: args = {} } = message.params || {};
    if (!name) {
      respondError(message.id, -32602, 'tools/call requires params.name');
      return;
    }
    respond(message.id, await callTool(name, args));
    return;
  }

  respondError(message.id, -32601, `Method not found: ${message.method}`);
}

let buffer = Buffer.alloc(0);

function parseMessages() {
  while (true) {
    if (buffer[0] === 123) {
      const lineEnd = buffer.indexOf('\n');
      if (lineEnd < 0) {
        return;
      }
      outputMode = 'line';
      const line = buffer.subarray(0, lineEnd).toString('utf8').replace(/\r$/, '');
      buffer = buffer.subarray(lineEnd + 1);
      try {
        void handleRequest(JSON.parse(line));
      } catch (error) {
        process.stderr.write(`coder-buddy-mcp parse error: ${error instanceof Error ? error.message : String(error)}\n`);
      }
      continue;
    }

    let headerEnd = buffer.indexOf('\r\n\r\n');
    let delimiterLength = 4;
    if (headerEnd < 0) {
      headerEnd = buffer.indexOf('\n\n');
      delimiterLength = 2;
    }
    if (headerEnd < 0) {
      return;
    }
    const header = buffer.subarray(0, headerEnd).toString('utf8');
    const match = header.match(/Content-Length:\s*(\d+)/i);
    if (!match) {
      buffer = buffer.subarray(headerEnd + delimiterLength);
      continue;
    }
    const length = Number(match[1]);
    const bodyStart = headerEnd + delimiterLength;
    const bodyEnd = bodyStart + length;
    if (buffer.length < bodyEnd) {
      return;
    }
    const body = buffer.subarray(bodyStart, bodyEnd).toString('utf8');
    buffer = buffer.subarray(bodyEnd);
    outputMode = 'content-length';
    try {
      void handleRequest(JSON.parse(body));
    } catch (error) {
      process.stderr.write(`coder-buddy-mcp parse error: ${error instanceof Error ? error.message : String(error)}\n`);
    }
  }
}

process.stdin.on('data', (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  parseMessages();
});
