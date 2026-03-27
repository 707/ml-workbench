#!/usr/bin/env node
/**
 * Agent Generator
 *
 * Generates platform-specific agent files from the shared source in .ai/agents/.
 * Each agent body is stored once in .ai/agents/{name}.md (no frontmatter).
 * Per-platform frontmatter is defined in scripts/agent-config.json.
 *
 * Outputs:
 *   .claude/agents/{name}.md  — Claude Code agents
 *   .gemini/agents/{name}.md  — Gemini CLI agents
 *
 * Usage:
 *   node scripts/gen-agents.js
 *   node scripts/gen-agents.js --dry-run   (preview only, no writes)
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const AI_AGENTS_DIR = path.join(ROOT, '.ai', 'agents');
const CLAUDE_AGENTS_DIR = path.join(ROOT, '.claude', 'agents');
const GEMINI_AGENTS_DIR = path.join(ROOT, '.gemini', 'agents');
const CONFIG_FILE = path.join(__dirname, 'agent-config.json');

const isDryRun = process.argv.includes('--dry-run');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function buildFrontmatter(config) {
  const lines = ['---'];
  for (const [key, value] of Object.entries(config)) {
    if (Array.isArray(value)) {
      lines.push(`${key}: [${value.map(v => `"${v}"`).join(', ')}]`);
    } else if (typeof value === 'string') {
      lines.push(`${key}: ${value}`);
    } else {
      lines.push(`${key}: ${value}`);
    }
  }
  lines.push('---');
  return lines.join('\n');
}

function generateAgent(name, body, platformConfig, outputDir) {
  const frontmatter = buildFrontmatter(platformConfig);
  const content = `${frontmatter}\n\n${body.trimStart()}`;
  const outputFile = path.join(outputDir, `${name}.md`);

  if (isDryRun) {
    console.log(`[dry-run] Would write: ${outputFile}`);
    console.log(`  Frontmatter keys: ${Object.keys(platformConfig).join(', ')}`);
    return;
  }

  fs.writeFileSync(outputFile, content, 'utf8');
  console.log(`  Written: ${outputFile}`);
}

function main() {
  // Read config
  if (!fs.existsSync(CONFIG_FILE)) {
    console.error(`Error: Config file not found: ${CONFIG_FILE}`);
    process.exit(1);
  }
  const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));

  // Ensure output dirs exist
  if (!isDryRun) {
    ensureDir(CLAUDE_AGENTS_DIR);
    ensureDir(GEMINI_AGENTS_DIR);
  }

  const agentNames = Object.keys(config);
  console.log(`Generating ${agentNames.length} agents for 2 platforms...\n`);

  let claudeCount = 0;
  let geminiCount = 0;
  const errors = [];

  for (const name of agentNames) {
    const sourceFile = path.join(AI_AGENTS_DIR, `${name}.md`);

    if (!fs.existsSync(sourceFile)) {
      errors.push(`Missing source: ${sourceFile}`);
      continue;
    }

    const body = fs.readFileSync(sourceFile, 'utf8');
    const agentConfig = config[name];

    console.log(`${name}:`);

    // Generate Claude agent
    if (agentConfig.claude) {
      generateAgent(name, body, agentConfig.claude, CLAUDE_AGENTS_DIR);
      claudeCount++;
    }

    // Generate Gemini agent
    if (agentConfig.gemini) {
      generateAgent(name, body, agentConfig.gemini, GEMINI_AGENTS_DIR);
      geminiCount++;
    }
  }

  console.log(`\nDone.`);
  if (isDryRun) {
    console.log(`[dry-run] No files written.`);
  } else {
    console.log(`  Claude agents: ${claudeCount} → ${CLAUDE_AGENTS_DIR}`);
    console.log(`  Gemini agents: ${geminiCount} → ${GEMINI_AGENTS_DIR}`);
  }

  if (errors.length > 0) {
    console.error('\nErrors:');
    for (const err of errors) {
      console.error(`  ${err}`);
    }
    process.exit(1);
  }
}

main();
