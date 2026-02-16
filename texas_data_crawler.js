#!/usr/bin/env node

const https = require('https');
const fs = require('fs');

// CDP Browser for deep metadata
class CDPBrowser {
    constructor(wsUrl) {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.id = 1;
        this.pending = new Map();
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl);
            this.ws.onopen = () => resolve();
            this.ws.onerror = (e) => reject(e);
            this.ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.id && this.pending.has(msg.id)) {
                    this.pending.get(msg.id)(msg.result || msg);
                    this.pending.delete(msg.id);
                }
            };
        });
    }

    async send(method, params = {}) {
        const mid = this.id++;
        this.ws.send(JSON.stringify({id: mid, method, params}));
        return new Promise(resolve => { this.pending.set(mid, resolve); });
    }

    async navigate(url) {
        await this.send('Runtime.enable');
        await this.send('Page.enable');
        return await this.send('Page.navigate', { url });
    }

    async evaluate(expression) {
        const result = await this.send('Runtime.evaluate', { expression });
        return result.result?.value;
    }

    async wait(ms) {
        return new Promise(r => setTimeout(r, ms));
    }

    close() {
        if (this.ws) this.ws.close();
    }
}

class TexasDataCrawler {
    constructor() {
        this.datasets = [];
        this.metadata = [];
        this.legalDatasets = [];
        this.categorized = { LAW_VERIFICATION: [], NEWS: [], ATTORNEY_RESOURCE: [] };
        this.browser = null;
        this.tabId = null;
    }

    // Use Socrata SODA API to get all datasets
    async discoverDatasetsViaAPI(limit = 100) {
        console.log('\n=== DISCOVERING DATASETS VIA API ===\n');
        
        const url = `https://data.texas.gov/api/views.json?limit=${limit}`;
        const data = await this.fetchJSON(url);
        
        this.datasets = data.map(d => ({
            id: d.id,
            name: d.name,
            description: d.description || '',
            category: d.category || '',
            tags: d.tags || [],
            viewCount: d.viewCount || 0,
            downloadCount: d.downloadCount || 0,
            createdAt: d.createdAt,
            updatedAt: d.rowsUpdatedAt,
            displayType: d.displayType,
            url: `https://data.texas.gov/dataset/${d.id}`
        }));
        
        console.log(`Discovered ${this.datasets.length} datasets via API`);
        return this.datasets;
    }

    fetchJSON(url) {
        return new Promise((resolve, reject) => {
            https.get(url, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch(e) {
                        reject(e);
                    }
                });
            }).on('error', reject);
        });
    }

    // Initialize browser for deep scraping
    async initBrowser() {
        const http = require('http');
        
        try {
            const tabsData = await new Promise((resolve, reject) => {
                http.get('http://localhost:9222/json', (res) => {
                    let data = '';
                    res.on('data', chunk => data += chunk);
                    res.on('end', () => resolve(JSON.parse(data)));
                }).on('error', reject);
            });
            
            const tab = tabsData.find(t => t.url.includes('data.texas.gov'));
            
            if (!tab) {
                console.log('No data.texas.gov tab - using API only');
                return false;
            }
            
            this.tabId = tab.id;
            this.browser = new CDPBrowser(tab.webSocketDebuggerUrl);
            await this.browser.connect();
            console.log('Browser connected for deep metadata');
            return true;
        } catch(e) {
            console.log('Browser not available:', e.message);
            return false;
        }
    }

    // Deep metadata extraction via browser
    async extractDeepMetadata(datasetIds = []) {
        if (!this.browser) {
            console.log('No browser available - skipping deep metadata');
            return [];
        }
        
        console.log('\n=== EXTRACTING DEEP METADATA VIA BROWSER ===\n');
        
        const deepMetadata = [];
        const ids = datasetIds.slice(0, 10); // Limit to 10 for time
        
        for (let i = 0; i < ids.length; i++) {
            const dsId = ids[i];
            console.log(`Processing ${i + 1}/${ids.length}: ${dsId}`);
            
            try {
                await this.browser.navigate(`https://data.texas.gov/dataset/${dsId}`);
                await this.browser.wait(2000);
                
                const meta = await this.browser.evaluate(`
                    JSON.stringify({
                        title: document.querySelector('h1')?.textContent?.trim() || '',
                        description: document.querySelector('[class*="description"], .dataset-header p')?.textContent?.trim() || '',
                        columns: Array.from(document.querySelectorAll('[class*="column"], th')).map(c => c.textContent.trim()).slice(0, 20),
                        rowCount: document.querySelector('[class*="row"], [class*="record"]')?.textContent?.trim() || '',
                        lastUpdated: document.querySelector('[class*="updated"], time')?.textContent?.trim() || '',
                        owner: document.querySelector('[class*="owner"], [class*="author"]')?.textContent?.trim() || '',
                        license: document.querySelector('[class*="license"]')?.textContent?.trim() || '',
                        tags: Array.from(document.querySelectorAll('[class*="tag"], .tag')).map(t => t.textContent.trim()),
                        dataPreview: Array.from(document.querySelectorAll('table tbody tr')).slice(0, 3).map(r => 
                            Array.from(r.querySelectorAll('td')).map(c => c.textContent.trim())
                        )
                    })
                `);
                
                const parsed = JSON.parse(meta);
                parsed.id = dsId;
                deepMetadata.push(parsed);
                
            } catch (e) {
                console.log(`  Error: ${e.message}`);
            }
        }
        
        console.log(`\nExtracted deep metadata for ${deepMetadata.length} datasets`);
        return deepMetadata;
    }

    // Filter for legal-related datasets
    filterLegalDatasets() {
        console.log('\n=== FILTERING LEGAL DATASETS ===\n');
        
        const legalKeywords = [
            'legal', 'law', 'court', 'attorney', 'license', 'permit',
            'regulation', 'statute', 'crime', 'criminal', 'justice',
            'violation', 'penalty', 'fine', 'compliance', 'regulatory',
            'insurance', 'tdi', 'txdps', 'bar', 'lawyer', 'filing',
            'case', 'judge', 'prosecutor', 'defense', 'litigation',
            'tarrant', 'harris', 'dallas', 'travis', 'bexar'
        ];
        
        this.legalDatasets = this.datasets.filter(ds => {
            const text = `${ds.name} ${ds.description} ${ds.category} ${ds.tags?.join(' ')}`.toLowerCase();
            return legalKeywords.some(kw => text.includes(kw));
        });
        
        console.log(`Found ${this.legalDatasets.length} legal-related datasets`);
        
        // Categorize
        this.categorized = {
            LAW_VERIFICATION: [],
            NEWS: [],
            ATTORNEY_RESOURCE: []
        };
        
        this.legalDatasets.forEach(ds => {
            const text = `${ds.name} ${ds.description}`.toLowerCase();
            
            if (text.includes('court') || text.includes('case') || text.includes('filing') || 
                text.includes('criminal') || text.includes('prosecution') || text.includes('dps') ||
                text.includes('crime') || text.includes('violation') || text.includes('penalty')) {
                this.categorized.LAW_VERIFICATION.push(ds);
            } else if (text.includes('news') || text.includes('report') || text.includes('press') || 
                       text.includes('publication') || text.includes('announcement')) {
                this.categorized.NEWS.push(ds);
            } else if (text.includes('attorney') || text.includes('lawyer') || text.includes('license') || 
                       text.includes('bar') || text.includes('permit') || text.includes('compliance')) {
                this.categorized.ATTORNEY_RESOURCE.push(ds);
            } else {
                this.categorized.LAW_VERIFICATION.push(ds);
            }
        });
        
        console.log('\nCategories:');
        console.log(`  LAW_VERIFICATION: ${this.categorized.LAW_VERIFICATION.length}`);
        console.log(`  NEWS: ${this.categorized.NEWS.length}`);
        console.log(`  ATTORNEY_RESOURCE: ${this.categorized.ATTORNEY_RESOURCE.length}`);
        
        return this.categorized;
    }

    // Measure API reachability
    async measureAPIReachability() {
        console.log('\n=== MEASURING API REACHABILITY ===\n');
        
        let reachable = 0;
        let total = Math.min(20, this.datasets.length);
        
        for (let i = 0; i < total; i++) {
            const ds = this.datasets[i];
            process.stdout.write(`Testing ${ds.id}... `);
            
            try {
                const url = `https://data.texas.gov/resource/${ds.id}.json?$limit=1`;
                await this.fetchJSON(url);
                console.log('OK');
                reachable++;
            } catch(e) {
                console.log('FAIL');
            }
        }
        
        const rate = (reachable / total * 100).toFixed(1);
        console.log(`\nAPI Reachability: ${rate}% (${reachable}/${total})`);
        return { reachable, total, rate };
    }

    // Generate quality scores
    generateQualityScores() {
        console.log('\n=== GENERATING QUALITY SCORES ===\n');
        
        const scores = this.legalDatasets.map(ds => {
            let score = 50; // base
            
            // Description quality
            if (ds.description && ds.description.length > 100) score += 15;
            if (ds.description && ds.description.length > 300) score += 10;
            
            // View/download count
            if (ds.viewCount > 100) score += 10;
            if (ds.downloadCount > 50) score += 10;
            
            // Has tags
            if (ds.tags && ds.tags.length > 0) score += 5;
            
            return {
                id: ds.id,
                name: ds.name,
                qualityScore: Math.min(100, score),
                metrics: {
                    hasDescription: !!ds.description,
                    descLength: ds.description?.length || 0,
                    viewCount: ds.viewCount,
                    downloadCount: ds.downloadCount,
                    hasTags: (ds.tags?.length || 0) > 0
                }
            };
        });
        
        const avgScore = scores.reduce((a, b) => a + b.qualityScore, 0) / scores.length;
        console.log(`Average Quality Score: ${avgScore.toFixed(1)}`);
        
        return { scores, averageScore: avgScore };
    }

    exportToJSON(filename = 'texas_datasets.json') {
        const output = {
            timestamp: new Date().toISOString(),
            source: 'data.texas.gov',
            method: 'Socrata SODA API + CDP Browser',
            totalDatasets: this.datasets.length,
            legalDatasets: this.legalDatasets.length,
            categories: {
                LAW_VERIFICATION: this.categorized.LAW_VERIFICATION.map(d => d.id),
                NEWS: this.categorized.NEWS.map(d => d.id),
                ATTORNEY_RESOURCE: this.categorized.ATTORNEY_RESOURCE.map(d => d.id)
            },
            datasets: this.datasets,
            legalDatasetsList: this.legalDatasets
        };
        
        fs.writeFileSync(filename, JSON.stringify(output, null, 2));
        console.log(`\nExported to ${filename}`);
        return output;
    }

    exportToCSV(filename = 'texas_datasets.csv') {
        const headers = ['id', 'name', 'description', 'category', 'tags', 'viewCount', 'downloadCount', 'displayType', 'url'];
        const rows = [headers.join(',')];
        
        this.datasets.forEach(ds => {
            const row = [
                ds.id || '',
                `"${(ds.name || '').replace(/"/g, '""')}"`,
                `"${(ds.description || '').replace(/"/g, '""').substring(0, 500)}"`,
                ds.category || '',
                `"${(ds.tags || []).join('; ')}"`,
                ds.viewCount || 0,
                ds.downloadCount || 0,
                ds.displayType || '',
                ds.url || ''
            ];
            rows.push(row.join(','));
        });
        
        fs.writeFileSync(filename, rows.join('\n'));
        console.log(`Exported to ${filename}`);
    }

    // Export for LangGraph integration
    exportForLangGraph(filename = 'texas_legal_datasets_langgraph.json') {
        const output = {
            metadata: {
                timestamp: new Date().toISOString(),
                source: 'data.texas.gov',
                experiment: 'Experiment 5 - Texas Data Pipeline',
                totalDatasets: this.datasets.length,
                legalDatasets: this.legalDatasets.length,
                categories: {
                    LAW_VERIFICATION: this.categorized.LAW_VERIFICATION.length,
                    NEWS: this.categorized.NEWS.length,
                    ATTORNEY_RESOURCE: this.categorized.ATTORNEY_RESOURCE.length
                }
            },
            datasets: {
                LAW_VERIFICATION: this.categorized.LAW_VERIFICATION,
                NEWS: this.categorized.NEWS,
                ATTORNEY_RESOURCE: this.categorized.ATTORNEY_RESOURCE
            },
            // Ready for LangGraph state
            langGraphState: {
                datasets_discovered: this.datasets.map(d => d.id),
                legal_datasets: this.legalDatasets.map(d => d.id),
                classification: {
                    LAW_VERIFICATION: this.categorized.LAW_VERIFICATION.map(d => d.id),
                    NEWS: this.categorized.NEWS.map(d => d.id),
                    ATTORNEY_RESOURCE: this.categorized.ATTORNEY_RESOURCE.map(d => d.id)
                },
                quality_scores: this.generateQualityScores()
            }
        };
        
        fs.writeFileSync(filename, JSON.stringify(output, null, 2));
        console.log(`Exported for LangGraph: ${filename}`);
        return output;
    }

    async run(withBrowser = true) {
        try {
            // 1. Discover all datasets via API
            await this.discoverDatasetsViaAPI(100);
            
            // 2. Extract metadata
            this.metadata = this.datasets;
            
            // 3. Initialize browser if requested
            if (withBrowser) {
                await this.initBrowser();
            }
            
            // 4. Filter legal datasets
            this.filterLegalDatasets();
            
            // 5. Deep metadata via browser
            if (this.browser) {
                const deepMeta = await this.extractDeepMetadata(
                    this.legalDatasets.map(d => d.id)
                );
                console.log(`Got ${deepMeta.length} deep metadata records`);
            }
            
            // 6. Measure API reachability
            const apiStats = await this.measureAPIReachability();
            
            // 7. Generate quality scores
            const quality = this.generateQualityScores();
            
            // 8. Export
            this.exportToJSON('/Users/owner/texas_datasets.json');
            this.exportToCSV('/Users/owner/texas_datasets.csv');
            this.exportForLangGraph('/Users/owner/texas_legal_datasets_langgraph.json');
            
            console.log('\n=== CRAWL COMPLETE ===');
            console.log(`\nSummary:`);
            console.log(`- Total datasets: ${this.datasets.length}`);
            console.log(`- Legal datasets: ${this.legalDatasets.length}`);
            console.log(`- API reachability: ${apiStats.rate}%`);
            console.log(`- Average quality score: ${quality.averageScore.toFixed(1)}`);
            
        } catch (e) {
            console.error('Error:', e.message);
        } finally {
            this.browser?.close();
        }
    }
}

// Run
const crawler = new TexasDataCrawler();
crawler.run(process.argv.includes('--browser'));
