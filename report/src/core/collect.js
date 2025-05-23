import { collect as collectCrux } from '../tools/crux.js';
import { collect as collectHar } from '../tools/har.js';
import { collect as collectPsi } from '../tools/psi.js';
import { collect as collectCode } from '../tools/code.js';
import { estimateTokenSize } from '../utils.js';

export async function getCrux(pageUrl, deviceType, options) {
  console.log('\n📊 [1/4] Collecting CrUX (Chrome User Experience) data...');
  const startTime = Date.now();
  const { full, summary, fromCache } = await collectCrux(pageUrl, deviceType, options);
  const duration = ((Date.now() - startTime) / 1000).toFixed(1);
  
  if (full.error && full.error.code === 404) {
    console.warn(`ℹ️  No CrUX data for that page (completed in ${duration}s).`);
  } else if (full.error) {
    console.error(`❌ Failed to collect CrUX data in ${duration}s.`, full.error.message);
  } else if (fromCache) {
    console.log(`✓ Loaded CrUX data from cache in ${duration}s. Estimated token size: ~`, estimateTokenSize(full));
  } else {
    console.log(`✅ Processed CrUX data in ${duration}s. Estimated token size: ~`, estimateTokenSize(full));
  }
  return { full, summary };
}

export async function getPsi(pageUrl, deviceType, options) {
  console.log('\n🚦 [2/4] Collecting PageSpeed Insights data...');
  const startTime = Date.now();
  const { full, summary, fromCache } = await collectPsi(pageUrl, deviceType, options);
  const duration = ((Date.now() - startTime) / 1000).toFixed(1);
  
  if (fromCache) {
    console.log(`✓ Loaded PSI data from cache in ${duration}s. Estimated token size: ~`, estimateTokenSize(full));
  } else {
    console.log(`✅ Processed PSI data in ${duration}s. Estimated token size: ~`, estimateTokenSize(full));
  }
  return { full, summary };
}

export async function getHar(pageUrl, deviceType, options) {
  console.log('\n🌐 [3/4] Collecting HAR data and page performance metrics...');
  const startTime = Date.now();
  const { har, harSummary, perfEntries, perfEntriesSummary, fullHtml, jsApi, fromCache } = await collectHar(pageUrl, deviceType, options);
  const duration = ((Date.now() - startTime) / 1000).toFixed(1);
  
  if (fromCache) {
    console.log(`✓ Loaded HAR data from cache in ${duration}s. Estimated token size: ~`, estimateTokenSize(har));
    console.log('✓ Loaded Performance Entries data from cache. Estimated token size: ~', estimateTokenSize(perfEntries));
    console.log('✓ Loaded full rendered HTML markup from cache. Estimated token size: ~', estimateTokenSize(fullHtml));
    console.log('✓ Loaded JS API data from cache. Estimated token size: ~', estimateTokenSize(jsApi));
  } else {
    console.log(`✅ Processed HAR data in ${duration}s. Estimated token size: ~`, estimateTokenSize(har));
    console.log('✅ Processed Performance Entries data. Estimated token size: ~', estimateTokenSize(perfEntries));
    console.log('✅ Processed full rendered HTML markup. Estimated token size: ~', estimateTokenSize(fullHtml));
    console.log('✅ Processed JS API data. Estimated token size: ~', estimateTokenSize(jsApi));
  }
  return { har, harSummary, perfEntries, perfEntriesSummary, fullHtml, jsApi };
}

export async function getCode(pageUrl, deviceType, requests, options) {
  console.log('\n📝 [4/4] Collecting page resources and code...');
  const startTime = Date.now();
  const { codeFiles, stats } = await collectCode(pageUrl, deviceType, requests, options);
  const duration = ((Date.now() - startTime) / 1000).toFixed(1);
  
  if (stats.fromCache === stats.total) {
    console.log(`✓ Loaded code from cache in ${duration}s. Estimated token size: ~`, estimateTokenSize(codeFiles));
  } else if (stats.fromCache > 0) {
    console.log(`✓ Partially loaded code from cache (${stats.fromCache}/${stats.total}) in ${duration}s. Estimated token size: ~`, estimateTokenSize(codeFiles));
  } else if (stats.failed > 0) {
    console.error(`❌ Failed to collect all project code in ${duration}s. Estimated token size: ~`, estimateTokenSize(codeFiles));
  } else {
    console.log(`✅ Processed project code in ${duration}s. Estimated token size: ~`, estimateTokenSize(codeFiles));
  }
  console.log(`   Total resources: ${stats.total}, Cached: ${stats.fromCache}, Failed: ${stats.failed}`);
  return { codeFiles, stats };
}

export default async function collectArtifacts(pageUrl, deviceType, options) {
  const { full: crux, summary: cruxSummary } = await getCrux(pageUrl, deviceType, options);
  const { full: psi, summary: psiSummary } = await getPsi(pageUrl, deviceType, options);
  const { har, harSummary, perfEntries, perfEntriesSummary, fullHtml, jsApi } = await getHar(pageUrl, deviceType, options);
  const requests = har.log.entries.map((e) => e.request.url);
  const { codeFiles: resources } = await getCode(pageUrl, deviceType, requests, options);

  return {
    har,
    harSummary,
    psi,
    psiSummary,
    resources,
    perfEntries,
    perfEntriesSummary,
    crux,
    cruxSummary,
    fullHtml,
    jsApi,
  };
}
