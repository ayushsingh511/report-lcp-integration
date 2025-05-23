import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { Tiktoken } from 'js-tiktoken/lite';
import cl100k_base from 'js-tiktoken/ranks/cl100k_base';
import collectArtifacts from './collect.js';
import {
  initializeSystem,
  cruxStep,
  cruxSummaryStep,
  psiStep,
  psiSummaryStep,
  harStep,
  harSummaryStep,
  perfStep,
  perfSummaryStep,
  htmlStep,
  codeStep,
  rulesStep,
  actionPrompt,
  resetStepCounter
} from '../prompts/index.js';
import { detectAEMVersion } from '../tools/aem.js';
import merge from '../tools/merge.js';
import { applyRules } from '../tools/rules.js';
import { estimateTokenSize, cacheResults, getCachedResults, getCachePath } from '../utils.js';
import { LLMFactory } from '../models/llm-factory.js';
import { DEFAULT_MODEL, getTokenLimits } from '../models/config.js';

/**
 * Creates message array with either full or summarized content
 */
function createMessages(pageData, useSummarized = false) {
  const {
    pageUrl, deviceType, cms, rulesSummary,
    resources, crux, psi, perfEntries, har,
    cruxSummary, psiSummary, perfEntriesSummary, harSummary
  } = pageData;

  // Reset step counter before creating a new sequence of messages
  resetStepCounter();
  
  const enc = new Tiktoken(cl100k_base);
  const tokenCounts = {};

  if (useSummarized) {
    // Log token counts for each component
    const messages = [
      new SystemMessage(initializeSystem(cms)),
      new HumanMessage(cruxSummaryStep(cruxSummary)),
      new HumanMessage(psiSummaryStep(psiSummary)),
      new HumanMessage(perfSummaryStep(perfEntriesSummary)),
      new HumanMessage(harSummaryStep(harSummary)),
      new HumanMessage(htmlStep(pageUrl, resources)),
      new HumanMessage(rulesStep(rulesSummary)),
      new HumanMessage(codeStep(pageUrl, resources, 10_000)),
      new HumanMessage(actionPrompt(pageUrl, deviceType)),
    ];
    
    tokenCounts['System Message'] = enc.encode(messages[0].content).length;
    tokenCounts['CRUX Summary'] = enc.encode(messages[1].content).length;
    tokenCounts['PSI Summary'] = enc.encode(messages[2].content).length;
    tokenCounts['Performance Summary'] = enc.encode(messages[3].content).length;
    tokenCounts['HAR Summary'] = enc.encode(messages[4].content).length;
    tokenCounts['HTML Content'] = enc.encode(messages[5].content).length;
    tokenCounts['Rules'] = enc.encode(messages[6].content).length;
    tokenCounts['Code Analysis'] = enc.encode(messages[7].content).length;
    tokenCounts['Action Prompt'] = enc.encode(messages[8].content).length;
    
    console.log('\n📊 Token counts (summarized mode):');
    Object.entries(tokenCounts).forEach(([key, value]) => {
      console.log(`  - ${key}: ${value.toLocaleString()} tokens`);
    });
    
    return messages;
  } else {
    const messages = [
      new SystemMessage(initializeSystem(cms)),
      new HumanMessage(cruxStep(crux)),
      new HumanMessage(psiStep(psi)),
      new HumanMessage(perfStep(perfEntries)),
      new HumanMessage(harStep(har)),
      new HumanMessage(htmlStep(pageUrl, resources)),
      new HumanMessage(rulesStep(rulesSummary)),
      new HumanMessage(codeStep(pageUrl, resources)),
      new HumanMessage(actionPrompt(pageUrl, deviceType)),
    ];
    
    tokenCounts['System Message'] = enc.encode(messages[0].content).length;
    tokenCounts['CRUX Data'] = enc.encode(messages[1].content).length;
    tokenCounts['PSI Data'] = enc.encode(messages[2].content).length;
    tokenCounts['Performance Entries'] = enc.encode(messages[3].content).length;
    tokenCounts['HAR Data'] = enc.encode(messages[4].content).length;
    tokenCounts['HTML Content'] = enc.encode(messages[5].content).length;
    tokenCounts['Rules'] = enc.encode(messages[6].content).length;
    tokenCounts['Code Analysis'] = enc.encode(messages[7].content).length;
    tokenCounts['Action Prompt'] = enc.encode(messages[8].content).length;
    
    console.log('\n📊 Token counts (full mode):');
    Object.entries(tokenCounts).forEach(([key, value]) => {
      console.log(`  - ${key}: ${value.toLocaleString()} tokens`);
    });
    
    return messages;
  }
}

/**
 * Invokes the LLM with a set of messages
 */
async function invokeLLM(llm, pageData, model, useSummarized = false) {
  const { pageUrl, deviceType } = pageData;
  const tokenLimits = getTokenLimits(model);
  const messages = createMessages(pageData, useSummarized);

  cacheResults(pageUrl, deviceType, 'prompt', messages);
  cacheResults(pageUrl, deviceType, 'prompt', messages.map((m) => m.content).join('\n---\n'));

  // Calculate token usage
  const enc = new Tiktoken(cl100k_base);
  const tokensLength = messages.map((m) => enc.encode(m.content).length).reduce((a, b) => a + b, 0);
  console.log(`\n📈 Total Prompt Tokens${useSummarized ? ' (simplified)' : ''}:`, tokensLength.toLocaleString());
  console.log(`📉 Token Limit for ${model}: Input=${tokenLimits.input.toLocaleString()}, Output=${tokenLimits.output.toLocaleString()}`);
  console.log(`📊 Usage: ${((tokensLength / tokenLimits.input) * 100).toFixed(1)}% of input limit`);

  // Check if we need to switch to summarized version
  if (!useSummarized && tokensLength > (tokenLimits.input - tokenLimits.output) * .9) {
    console.log('\n⚠️  Context window limit hit. Trying with summarized prompt...');
    return invokeLLM(llm, pageData, model, true);
  }

  try {
    console.log(`\n🤖 Sending request to ${model}...`);
    const startTime = Date.now();
    
    // Direct invocation
    const result = await llm.invoke(messages);
    const endTime = Date.now();
    const duration = ((endTime - startTime) / 1000).toFixed(1);
    
    console.log(`✅ Response received in ${duration}s`);
    
    cacheResults(pageUrl, deviceType, 'report', result, '', model);
    const path = cacheResults(pageUrl, deviceType, 'report', result.content, '', model);
    console.log('✅ CWV report generated at:', path);
    return result;
  } catch (error) {
    console.error('❌ Failed to generate report for', pageData.pageUrl);

    if (error.code === 400 && !useSummarized) { // Token limit reached, retry with summarized if we haven't yet
      console.log('Context window limit hit. Retrying with summarized prompt...');
      return invokeLLM(llm, pageData, model, true);
    } else if (error.code === 400) {
      console.log('Context window limit hit, even with summarized prompt.', error);
    } else if (error.code === 403) {
      console.log('Invalid API key.', error.message);
    } else if (error.status === 429) {
      console.log('Rate limit hit. Try again in 5 mins...', error);
    } else {
      console.error(error);
    }
    return error;
  }
}

export default async function runPrompt(pageUrl, deviceType, options = {}) {
  // Get model from options or use default
  const model = options.model || DEFAULT_MODEL;
  
  console.log(`\n🔍 Starting report generation for ${pageUrl}`);
  console.log(`📱 Device: ${deviceType}`);
  console.log(`🤖 Model: ${model}`);
  
  // Check cache first if not skipping
  let result;
  if (!options.skipCache) {
    console.log('\n📂 Checking cache...');
    result = getCachedResults(pageUrl, deviceType, 'report', '', model);
    if (result) {
      const path = getCachePath(pageUrl, deviceType, 'report', '', true, model);
      console.log('✅ Report already exists at', path);
      return result;
    }
    console.log('❌ No cached report found');
  }

  // Perform data collection before running the model, so we don't waste calls if an error occurs
  console.log('\n📥 Starting data collection...');
  const startTime = Date.now();
  
  const {
    har,
    harSummary,
    psi,
    psiSummary,
    resources,
    crux,
    cruxSummary,
    perfEntries,
    perfEntriesSummary,
    fullHtml,
    jsApi,
  } = await collectArtifacts(pageUrl, deviceType, options);
  
  const collectionTime = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`✅ Data collection completed in ${collectionTime}s`);

  console.log('\n📋 Processing rules...');
  const rulesStartTime = Date.now();
  const report = merge(pageUrl, deviceType);
  const { summary: rulesSummary, fromCache } = await applyRules(pageUrl, deviceType, options, { crux, psi, har, perfEntries, resources, fullHtml, jsApi, report });
  const rulesTime = ((Date.now() - rulesStartTime) / 1000).toFixed(1);
  
  if (fromCache) {
    console.log(`✓ Loaded rules from cache in ${rulesTime}s. Estimated token size: ~`, estimateTokenSize(rulesSummary));
  } else {
    console.log(`✅ Processed rules in ${rulesTime}s. Estimated token size: ~`, estimateTokenSize(rulesSummary));
  }

  const cms = detectAEMVersion(har.log.entries[0].headers, fullHtml);
  console.log('🏢 AEM Version:', cms);

  // Create LLM instance using the factory
  console.log('\n🔧 Initializing LLM...');
  const llm = LLMFactory.createLLM(model, options.llmOptions || {});

  // Organize all data into one object for easier passing
  const pageData = {
    pageUrl, deviceType, cms, rulesSummary, resources,
    crux, psi, perfEntries, har,
    cruxSummary, psiSummary, perfEntriesSummary, harSummary
  };

  // Invoke LLM and handle retries automatically
  console.log('\n🚀 Generating performance report...');
  return invokeLLM(llm, pageData, model, false);
}
