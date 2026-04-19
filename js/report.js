const REPORT_API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : '/api/v1';

const REPORT_STORAGE_KEY = 'scet:last-report';

document.addEventListener('DOMContentLoaded', () => {
    const shareBtn = document.getElementById('shareReportBtn');
    const printBtn = document.getElementById('printReportBtn');

    if (shareBtn) {
        shareBtn.addEventListener('click', copyReportLink);
    }

    if (printBtn) {
        printBtn.addEventListener('click', () => window.print());
    }

    loadReport();
});

async function loadReport() {
    const params = new URLSearchParams(window.location.search);
    const fallback = loadFallbackReport();

    const payload = {
        title: params.get('title') || fallback.title || '',
        creator: params.get('creator') || fallback.creator || '',
        year: params.get('year') || fallback.year || '',
        type: params.get('type') || fallback.type || '',
        jurisdiction: params.get('jurisdiction') || fallback.jurisdiction || 'US',
        source: params.get('source') || fallback.source || 'Multiple Sources',
        source_url: params.get('source_url') || fallback.source_url || ''
    };

    if (!payload.title) {
        renderEmptyState();
        return;
    }

    try {
        const apiParams = new URLSearchParams(payload);
        const response = await fetch(`${REPORT_API_BASE}/report?${apiParams.toString()}`);
        if (!response.ok) {
            throw new Error('Failed to fetch report');
        }

        const data = await response.json();
        renderReport(data);
    } catch (error) {
        console.error('Report load error:', error);
        renderFallbackPayload(payload);
    }
}

function loadFallbackReport() {
    try {
        return JSON.parse(localStorage.getItem(REPORT_STORAGE_KEY) || '{}');
    } catch (error) {
        return {};
    }
}

function renderReport(data) {
    const tag = data.tag || {};
    const confidence = Number(data.confidence_score || tag.confidence_score || tag.confidence || 0);
    const status = String(data.status || tag.status || 'UNKNOWN').toUpperCase();
    const statusClass = status === 'PUBLIC_DOMAIN'
        ? 'badge-public'
        : status === 'PROTECTED'
            ? 'badge-protected'
            : 'badge-unknown';

    setText('reportTitle', `Copyright Validation Report: ${data.title}`);
    setText('workTitle', data.title);
    setText('workCreator', data.creator || 'Creator unknown');
    setHtml('statusBadge', `<span class="result-badge ${statusClass}">${escapeHtml(prettyStatus(status))}</span>`);
    setText('pubYear', data.publication_year || 'Unknown');
    setText('reportContentType', prettyStatus(data.content_type || 'unknown'));
    setText('reportJurisdiction', prettyJurisdiction(data.jurisdiction || 'US'));
    setText('dataSource', data.source || 'Multiple Sources');
    setText('statusText', data.summary || data.status_text || 'No status summary available.');
    setText('expiryDate', tag.expiry_tag || data.expiry_date || 'Not determined');
    setText('yearsRemaining', deriveYearsRemaining(tag));
    setText('confidenceScore', `${Math.round(confidence * 100)}%`);
    setText('confidenceBadgeText', buildConfidenceLabel(confidence));
    setStyle('confidenceFill', 'width', `${confidence * 100}%`);
    setText(
        'confidenceExplanation',
        confidence >= 0.8
            ? 'High confidence based on strong metadata and rule-based signals.'
            : confidence >= 0.6
                ? 'Moderate confidence. Verify with official records for legal decisions.'
                : 'Limited confidence. More source verification is recommended.'
    );

    const reasoningHtml = `
        <p>${escapeHtml(data.reasoning || tag.ai_reasoning || 'No reasoning available.')}</p>
        <ul>
            <li>Jurisdiction: ${escapeHtml(prettyJurisdiction(data.jurisdiction || 'US'))}</li>
            <li>Publication year: ${escapeHtml(String(data.publication_year || 'Unknown'))}</li>
            <li>Content type: ${escapeHtml(prettyStatus(data.content_type || 'unknown'))}</li>
        </ul>
    `;
    setHtml('reasoningBox', reasoningHtml);

    renderPillList('allowedUsesList', data.allowed_uses || []);
    renderSources('sourcesList', data.sources_consulted || []);
}

function renderFallbackPayload(payload) {
    const pseudoStatus = payload.status || 'UNKNOWN';
    const statusClass = pseudoStatus === 'PUBLIC_DOMAIN'
        ? 'badge-public'
        : pseudoStatus === 'PROTECTED'
            ? 'badge-protected'
            : 'badge-unknown';

    setText('reportTitle', `Copyright Validation Report: ${payload.title}`);
    setText('workTitle', payload.title);
    setText('workCreator', payload.creator || 'Creator unknown');
    setHtml('statusBadge', `<span class="result-badge ${statusClass}">${escapeHtml(prettyStatus(pseudoStatus))}</span>`);
    setText('pubYear', payload.year || 'Unknown');
    setText('reportContentType', prettyStatus(payload.type || 'unknown'));
    setText('reportJurisdiction', prettyJurisdiction(payload.jurisdiction || 'US'));
    setText('dataSource', payload.source || 'Multiple Sources');
    setText('statusText', 'Basic report details were restored from local data. Open the report again online for full reasoning and confidence.');
    setText('confidenceBadgeText', 'Stored local snapshot');
    renderPillList('allowedUsesList', []);
    renderSources('sourcesList', [{ name: payload.source || 'Stored report snapshot', url: payload.source_url || '' }]);
}

function renderEmptyState() {
    setText('reportTitle', 'Copyright Validation Report');
    setText('workTitle', 'No report selected');
    setText('workCreator', 'Open a report from the search page to view details here.');
    setText('statusText', 'No report data was found in the URL or local storage.');
}

function renderPillList(targetId, items) {
    const target = document.getElementById(targetId);
    if (!target) {
        return;
    }

    if (!items.length) {
        target.innerHTML = '<div class="source-item"><span class="source-name">No allowed-use summary available</span></div>';
        return;
    }

    target.innerHTML = items.map((item) => `
        <div class="source-item">
            <span class="source-name">${escapeHtml(item)}</span>
        </div>
    `).join('');
}

function renderSources(targetId, sources) {
    const target = document.getElementById(targetId);
    if (!target) {
        return;
    }

    target.innerHTML = sources
        .filter((source) => source && (source.used !== false))
        .map((source) => {
            const name = escapeHtml(source.name || 'Source');
            if (source.url) {
                return `
                    <a class="source-item" href="${escapeHtml(source.url)}" target="_blank" rel="noopener">
                        <span class="source-name">${name}</span>
                    </a>
                `;
            }
            return `
                <div class="source-item">
                    <span class="source-name">${name}</span>
                </div>
            `;
        }).join('') || '<div class="source-item"><span class="source-name">No source list available</span></div>';
}

function deriveYearsRemaining(tag) {
    if (!tag || !tag.expiry_info) {
        return 'N/A';
    }
    if (tag.status === 'PUBLIC_DOMAIN') {
        return '0';
    }
    const match = String(tag.expiry_info).match(/(\d+)\s+years?\s+remaining/i);
    return match ? match[1] : tag.expiry_info;
}

function buildConfidenceLabel(score) {
    if (score >= 0.8) return 'High confidence assessment';
    if (score >= 0.6) return 'Moderate confidence assessment';
    return 'Limited-confidence estimate';
}

async function copyReportLink() {
    await navigator.clipboard.writeText(window.location.href);
    showToast('Report link copied to clipboard.', 'success');
}

function prettyStatus(value) {
    return String(value || '').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function prettyJurisdiction(value) {
    const map = {
        US: 'United States',
        EU: 'European Union',
        UK: 'United Kingdom',
        IN: 'India',
        CA: 'Canada',
        AU: 'Australia',
        JP: 'Japan'
    };
    return map[value] || value;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function setHtml(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.innerHTML = value;
    }
}

function setStyle(id, property, value) {
    const element = document.getElementById(id);
    if (element) {
        element.style[property] = value;
    }
}

function showToast(message, type) {
    let region = document.getElementById('toastRegion');
    if (!region) {
        region = document.createElement('div');
        region.id = 'toastRegion';
        region.className = 'toast-region';
        document.body.appendChild(region);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type || 'info'}`;
    toast.textContent = message;
    region.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add('is-visible');
    });

    setTimeout(() => {
        toast.classList.remove('is-visible');
        setTimeout(() => toast.remove(), 220);
    }, 2200);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = String(text ?? '');
    return div.innerHTML;
}
