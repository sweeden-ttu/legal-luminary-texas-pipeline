#!/usr/bin/env node

const https = require('https');
const fs = require('fs');

// All Texas data sources from RUBRIC.md and settings.py
const TEXAS_DATA_SOURCES = {
    // Texas Open Data Portal (Socrata) - MAIN SOURCE
    'data.texas.gov': {
        type: 'socrata',
        api: 'https://data.texas.gov/api/views.json',
        baseUrl: 'https://data.texas.gov',
        description: 'Texas Open Data Portal - Main Socrata source',
        legalKeywords: ['tdcj', 'tdi', 'tdlr', 'insurance', 'license', 'court', 'crime', 'prison', 'abuse', 'neglect']
    },
    
    // Texas Legislature & Statutes
    'capitol.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://capitol.texas.gov',
        description: 'Texas Capitol / Legislature',
        legalKeywords: ['legislature', 'bill', 'resolution', 'session', 'law']
    },
    
    'statutes.capitol.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://statutes.capitol.texas.gov',
        description: 'Texas Statutes full text',
        legalKeywords: ['penal code', 'civil statute', 'chapter', 'section', 'law', 'regulation']
    },
    
    // Texas Attorney General
    'www.texasattorneygeneral.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://www.texasattorneygeneral.gov',
        description: 'Texas Attorney General',
        legalKeywords: ['attorney general', 'opinion', 'legal', 'consumer', 'crime']
    },
    
    // Texas Courts
    'txcourts.gov': {
        type: 'api',
        api: 'https://search.txcourts.gov/api',
        baseUrl: 'https://txcourts.gov',
        description: 'Texas Judicial Branch',
        legalKeywords: ['court', 'case', 'judicial', 'docket', 'trial']
    },
    
    // Texas Secretary of State
    'www.sos.state.tx.us': {
        type: 'api',
        api: null,
        baseUrl: 'https://www.sos.state.tx.us',
        description: 'Texas Secretary of State',
        legalKeywords: ['notary', 'corporation', 'election', 'filing']
    },
    
    // Texas Legislative Reference Library
    'lrl.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://lrl.texas.gov',
        description: 'Texas Legislative Reference Library',
        legalKeywords: ['bill', 'legislation', 'member', 'committee', 'session']
    },
    
    // State Law Library
    'sll.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://sll.texas.gov',
        description: 'Texas State Law Library',
        legalKeywords: ['law', 'legal', 'statute', 'code', 'research']
    },
    
    // Texas Comptroller
    'comptroller.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://comptroller.texas.gov',
        description: 'Texas Comptroller',
        legalKeywords: ['tax', 'budget', 'finance', 'revenue']
    },
    
    // Texas Governor
    'gov.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://gov.texas.gov',
        description: 'Texas Governor',
        legalKeywords: ['executive', 'order', 'proclamation', 'appointment']
    },
    
    // Texas Legislature Online
    'www.legis.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://www.legis.texas.gov',
        description: 'Texas Legislature Online',
        legalKeywords: ['bill', 'legislation', 'hearing', 'committee']
    },
    
    // Texas Legislative Budget Board
    'www.lbb.texas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://www.lbb.texas.gov',
        description: 'Texas Legislative Budget Board',
        legalKeywords: ['budget', 'appropriation', 'fiscal']
    },
    
    // eFile Texas
    'efiletexas.gov': {
        type: 'api',
        api: null,
        baseUrl: 'https://www.efiletexas.gov',
        description: 'Texas eFiling Portal',
        legalKeywords: ['filing', 'court', 'document', 'efile']
    },
    
    // Bell County (local government)
    'www.bellcountytx.com': {
        type: 'api',
        api: null,
        baseUrl: 'https://www.bellcountytx.com',
        description: 'Bell County Official Site',
        legalKeywords: ['court', 'clerk', 'district', 'county', 'legal']
    }
};

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

class TexasMultiSourceCrawler {
    constructor() {
        this.datasets = {};
        this.legalDatasets = [];
        this.categorized = { LAW_VERIFICATION: [], NEWS: [], ATTORNEY_RESOURCE: [] };
        this.browser = null;
        this.qualityScores = [];
        this.apiReachability = {};
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

    async checkReachability(url) {
        return new Promise((resolve) => {
            https.get(url, (res) => {
                resolve(res.statusCode === 200);
            }).on('error', () => resolve(false));
        });
    }

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
            
            this.browser = new CDPBrowser(tab.webSocketDebuggerUrl);
            await this.browser.connect();
            console.log('Browser connected');
            return true;
        } catch(e) {
            console.log('Browser not available:', e.message);
            return false;
        }
    }

    // Crawl Socrata-based source
    async crawlSocrata(source, limit = 100) {
        console.log(`\n=== Crawling ${source} (Socrata) ===`);
        
        try {
            const url = `${TEXAS_DATA_SOURCES[source].api}?limit=${limit}`;
            const data = await this.fetchJSON(url);
            
            const datasets = data.map(d => ({
                id: d.id,
                name: d.name,
                description: d.description || '',
                category: d.category || '',
                tags: d.tags || [],
                viewCount: d.viewCount || 0,
                downloadCount: d.downloadCount || 0,
                displayType: d.displayType,
                source: source,
                sourceType: 'socrata',
                url: `https://data.texas.gov/dataset/${d.id}`,
                apiUrl: `https://data.texas.gov/resource/${d.id}.json`
            }));
            
            this.datasets[source] = datasets;
            this.apiReachability[source] = true;
            console.log(`  Found ${datasets.length} datasets`);
            return datasets;
        } catch(e) {
            console.log(`  Error: ${e.message}`);
            this.apiReachability[source] = false;
            return [];
        }
    }

    // Crawl generic API/scraper source
    async crawlGeneric(source) {
        console.log(`\n=== Crawling ${source} ===`);
        
        const config = TEXAS_DATA_SOURCES[source];
        
        // Check reachability
        const reachable = await this.checkReachability(config.baseUrl);
        this.apiReachability[source] = reachable;
        console.log(`  Reachability: ${reachable ? 'OK' : 'FAILED'}`);
        
        if (!reachable) {
            return [];
        }
        
        if (!this.browser) {
            console.log('  No browser - skipping');
            return [];
        }
        
        try {
            await this.browser.navigate(config.baseUrl);
            await this.browser.wait(2000);
            
            // Extract legal-relevant links
            const links = await this.browser.evaluate(`
                JSON.stringify(Array.from(document.links)
                    .filter(l => l.href && l.href.includes('${source}') && 
                        !l.href.includes('javascript') &&
                        !l.href.includes('mailto'))
                    .slice(0, 100)
                    .map(l => ({
                        text: l.textContent.trim().substring(0, 80),
                        href: l.href
                    })))
            `);
            
            const parsed = JSON.parse(links);
            console.log(`  Found ${parsed.length} links`);
            
            // Filter by legal keywords
            const legalLinks = parsed.filter(l => {
                const text = l.text.toLowerCase();
                return config.legalKeywords.some(kw => text.includes(kw));
            });
            
            console.log(`  Legal-relevant: ${legalLinks.length}`);
            
            this.datasets[source] = legalLinks.map(l => ({
                name: l.text,
                url: l.href,
                source: source,
                sourceType: 'scraper',
                description: `Scraped from ${config.description}`
            }));
            
            return this.datasets[source];
            
        } catch(e) {
            console.log(`  Error: ${e.message}`);
            return [];
        }
    }

    // Crawl all sources
    async crawlAllSources() {
        console.log('\n========================================');
        console.log('CRAWLING ALL TEXAS DATA SOURCES');
        console.log('========================================');
        
        // 1. Crawl data.texas.gov (main Socrata source)
        await this.crawlSocrata('data.texas.gov', 100);
        
        // 2. Crawl other sources with browser
        if (this.browser) {
            for (const source of Object.keys(TEXAS_DATA_SOURCES)) {
                if (source !== 'data.texas.gov') {
                    await this.crawlGeneric(source);
                }
            }
        }
        
        return this.datasets;
    }

    filterLegalDatasets() {
        console.log('\n=== FILTERING LEGAL DATASETS ===\n');
        
        // Collect all datasets
        let allDatasets = [];
        for (const source of Object.keys(this.datasets)) {
            allDatasets = allDatasets.concat(this.datasets[source]);
        }
        
        const legalKeywords = [
            'legal', 'law', 'court', 'attorney', 'license', 'permit',
            'regulation', 'statute', 'crime', 'criminal', 'justice',
            'violation', 'penalty', 'fine', 'compliance', 'regulatory',
            'insurance', 'tdi', 'txdps', 'bar', 'lawyer', 'filing',
            'case', 'judge', 'prosecutor', 'defense', 'litigation',
            'tarrant', 'harris', 'dallas', 'travis', 'bexar', 'bell',
            'child', 'abuse', 'neglect', 'prison', 'release', 'inmate',
            'tdcj', 'tdlr', 'bill', 'legislation', 'session'
        ];
        
        this.legalDatasets = allDatasets.filter(ds => {
            const text = `${ds.name} ${ds.description || ''}`.toLowerCase();
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
            const text = `${ds.name} ${ds.description || ''}`.toLowerCase();
            
            if (text.includes('court') || text.includes('case') || text.includes('filing') || 
                text.includes('criminal') || text.includes('prosecution') || text.includes('dps') ||
                text.includes('crime') || text.includes('violation') || text.includes('penalty') ||
                text.includes('prison') || text.includes('inmate') || text.includes('release') ||
                text.includes('statute') || text.includes('penal code')) {
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

    async measureAPIReachability() {
        console.log('\n=== MEASURING API REACHABILITY ===\n');
        
        let reachable = 0;
        let total = 0;
        
        // Test data.texas.gov API
        for (const ds of this.datasets['data.texas.gov']?.slice(0, 10) || []) {
            total++;
            process.stdout.write(`Testing ${ds.id}... `);
            try {
                await this.fetchJSON(`https://data.texas.gov/resource/${ds.id}.json?$limit=1`);
                console.log('OK');
                reachable++;
            } catch(e) {
                console.log('FAIL');
            }
        }
        
        // Test other sources
        for (const source of Object.keys(TEXAS_DATA_SOURCES)) {
            if (source !== 'data.texas.gov') {
                total++;
                process.stdout.write(`Testing ${source}... `);
                try {
                    const reachable_now = await this.checkReachability(TEXAS_DATA_SOURCES[source].baseUrl);
                    this.apiReachability[source] = reachable_now;
                    console.log(reachable_now ? 'OK' : 'FAIL');
                    if (reachable_now) reachable++;
                } catch(e) {
                    console.log('FAIL');
                }
            }
        }
        
        const rate = total > 0 ? (reachable / total * 100).toFixed(1) : 0;
        console.log(`\nOverall API Reachability: ${rate}% (${reachable}/${total})`);
        
        return { reachable, total, rate };
    }

    generateQualityScores() {
        console.log('\n=== GENERATING QUALITY SCORES ===\n');
        
        this.qualityScores = this.legalDatasets.map(ds => {
            let score = 50;
            
            if (ds.description && ds.description.length > 100) score += 15;
            if (ds.description && ds.description.length > 300) score += 10;
            if (ds.viewCount > 100) score += 10;
            if (ds.downloadCount > 50) score += 10;
            if (ds.tags && ds.tags.length > 0) score += 5;
            
            return {
                id: ds.id || ds.url,
                name: ds.name,
                qualityScore: Math.min(100, score)
            };
        });
        
        const avgScore = this.qualityScores.reduce((a, b) => a + b.qualityScore, 0) / this.qualityScores.length;
        console.log(`Average Quality Score: ${avgScore.toFixed(1)}`);
        
        return { scores: this.qualityScores, averageScore: avgScore };
    }

    exportAll(filename = 'texas_multi_source_data.json') {
        const output = {
            timestamp: new Date().toISOString(),
            sources: TEXAS_DATA_SOURCES,
            sourceCount: Object.keys(TEXAS_DATA_SOURCES).length,
            sourcesCrawled: Object.keys(this.datasets).length,
            reachability: this.apiReachability,
            totalDatasets: Object.values(this.datasets).reduce((a, b) => a + b.length, 0),
            legalDatasets: this.legalDatasets.length,
            categories: {
                LAW_VERIFICATION: this.categorized.LAW_VERIFICATION.length,
                NEWS: this.categorized.NEWS.length,
                ATTORNEY_RESOURCE: this.categorized.ATTORNEY_RESOURCE.length
            },
            datasetsBySource: this.datasets,
            categorized: {
                LAW_VERIFICATION: this.categorized.LAW_VERIFICATION,
                NEWS: this.categorized.NEWS,
                ATTORNEY_RESOURCE: this.categorized.ATTORNEY_RESOURCE
            },
            qualityScores: this.qualityScores,
            langGraphReady: {
                metadata: {
                    experiment: 'Experiment 5 - Texas Data Pipeline',
                    sources: Object.keys(TEXAS_DATA_SOURCES),
                    totalSources: Object.keys(TEXAS_DATA_SOURCES).length,
                    totalDatasets: Object.values(this.datasets).reduce((a, b) => a + b.length, 0)
                },
                datasets_discovered: this.legalDatasets.map(d => d.id || d.url),
                classification: {
                    LAW_VERIFICATION: this.categorized.LAW_VERIFICATION.map(d => d.id || d.url),
                    NEWS: this.categorized.NEWS.map(d => d.id || d.url),
                    ATTORNEY_RESOURCE: this.categorized.ATTORNEY_RESOURCE.map(d => d.id || d.url)
                }
            }
        };
        
        fs.writeFileSync(filename, JSON.stringify(output, null, 2));
        console.log(`\nExported to ${filename}`);
        
        // Also export CSVs
        this.exportCSV('/Users/owner/texas_all_sources_datasets.csv');
        this.exportLegalCSV('/Users/owner/texas_legal_datasets.csv');
        
        return output;
    }

    exportCSV(filename) {
        const rows = ['name,source,sourceType,url,description'];
        
        for (const ds of this.legalDatasets) {
            const row = [
                `"${(ds.name || '').replace(/"/g, '""')}"`,
                ds.source || 'unknown',
                ds.sourceType || 'unknown',
                ds.url || '',
                `"${(ds.description || '').replace(/"/g, '""').substring(0, 300)}"`
            ];
            rows.push(row.join(','));
        }
        
        fs.writeFileSync(filename, rows.join('\n'));
        console.log(`Exported CSV to ${filename}`);
    }
    
    exportLegalCSV(filename) {
        const rows = ['id,name,category,url'];
        
        this.legalDatasets.forEach(ds => {
            let category = 'LAW_VERIFICATION';
            const text = `${ds.name} ${ds.description || ''}`.toLowerCase();
            
            if (text.includes('news') || text.includes('report') || text.includes('press')) {
                category = 'NEWS';
            } else if (text.includes('attorney') || text.includes('license') || text.includes('bar')) {
                category = 'ATTORNEY_RESOURCE';
            }
            
            const row = [
                ds.id || ds.url.substring(0, 20),
                `"${(ds.name || '').replace(/"/g, '""').substring(0, 100)}"`,
                category,
                ds.url || ''
            ];
            rows.push(row.join(','));
        });
        
        fs.writeFileSync(filename, rows.join('\n'));
        console.log(`Exported legal datasets to ${filename}`);
    }

    async run(withBrowser = true) {
        try {
            // Initialize browser if requested
            if (withBrowser) {
                await this.initBrowser();
            }
            
            // Crawl all sources
            await this.crawlAllSources();
            
            // Filter legal datasets
            this.filterLegalDatasets();
            
            // Measure API reachability
            const apiStats = await this.measureAPIReachability();
            
            // Generate quality scores
            this.generateQualityScores();
            
            // Export
            this.exportAll('/Users/owner/texas_multi_source_data.json');
            
            console.log('\n=== CRAWL COMPLETE ===');
            console.log(`\nSummary:`);
            console.log(`- Sources configured: ${Object.keys(TEXAS_DATA_SOURCES).length}`);
            console.log(`- Sources crawled: ${Object.keys(this.datasets).length}`);
            console.log(`- Total datasets: ${Object.values(this.datasets).reduce((a, b) => a + b.length, 0)}`);
            console.log(`- Legal datasets: ${this.legalDatasets.length}`);
            console.log(`- API reachability: ${apiStats.rate}%`);
            
        } catch (e) {
            console.error('Error:', e.message);
        } finally {
            this.browser?.close();
        }
    }
}

// Run
const crawler = new TexasMultiSourceCrawler();
crawler.run(process.argv.includes('--browser'));
