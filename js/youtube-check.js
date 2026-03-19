// YouTube Music Copyright Checker frontend
const songInput = document.getElementById('ytSongTitle');
const artistInput = document.getElementById('ytArtistName');
const checkBtn = document.getElementById('ytCheckBtn');
const loading = document.getElementById('ytLoading');
const errorBox = document.getElementById('ytError');
const resultSection = document.getElementById('ytResultSection');
const resultCard = document.getElementById('ytResultCard');

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

checkBtn.addEventListener('click', runYoutubeCheck);
songInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') runYoutubeCheck();
});
artistInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') runYoutubeCheck();
});

async function runYoutubeCheck() {
    const title = songInput.value.trim();
    const artist = artistInput.value.trim();

    if (!title) {
        showError('Please enter Song Title.');
        return;
    }

    hideError();
    setLoading(true);
    resultSection.classList.add('hidden');

    try {
        const params = new URLSearchParams({ title, artist });
        const response = await fetch(`${API_BASE}/api/youtube-check?${params.toString()}`);
        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Failed to check copyright');
        }

        renderMusicResultCard(data);
        resultSection.classList.remove('hidden');
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
        showError(err.message || 'Could not fetch metadata. Try again.');
    } finally {
        setLoading(false);
    }
}

function renderMusicResultCard(data) {
    const riskClass =
        data.youtube_usage_risk === 'HIGH' ? 'badge-protected' :
        data.youtube_usage_risk === 'LOW' ? 'badge-public' : 'badge-unknown';

    const usesHtml = (data.allowed_uses || []).map((u) => `<li>${escapeHtml(u)}</li>`).join('');
    const sourcesHtml = (data.sources || [])
        .filter((s) => s.used)
        .map((s) => {
            if (s.url) {
                return `<li><a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.name)}</a></li>`;
            }
            return `<li>${escapeHtml(s.name)}</li>`;
        })
        .join('') || '<li>Metadata API</li>';

    resultCard.innerHTML = `
        <div class="smart-tag">
            <div class="tag-header">
                <span class="tag-emoji">🎵</span>
                <span class="tag-status">YouTube Music Copyright Checker</span>
            </div>

            <div class="music-card-grid">
                <div class="music-row"><strong>Song:</strong> ${escapeHtml(data.song || 'Unknown')}</div>
                <div class="music-row"><strong>Artist:</strong> ${escapeHtml(data.artist || 'Unknown')}</div>
                <div class="music-row"><strong>Release Year:</strong> ${escapeHtml(String(data.release_year || 'Unknown'))}</div>
                <div class="music-row"><strong>Publisher / Label:</strong> ${escapeHtml(data.publisher_label || 'Unknown')}</div>
                <div class="music-row"><strong>Copyright Status:</strong> ${escapeHtml(data.copyright_status || 'UNCLEAR')}</div>
                <div class="music-row"><strong>YouTube Usage Risk:</strong> <span class="result-badge ${riskClass}">${escapeHtml(data.youtube_usage_risk || 'MEDIUM')}</span></div>
            </div>

            <div class="tag-section">
                <h4>Allowed Uses</h4>
                <ul class="music-list">${usesHtml}</ul>
            </div>

            <div class="tag-section">
                <h4>Recommendation</h4>
                <p>${escapeHtml(data.recommendation || 'Use licensed or royalty-free music.')}</p>
            </div>

            <div class="tag-section">
                <h4>Confidence Score</h4>
                <p>${escapeHtml(String(data.confidence_score || 0))}</p>
            </div>

            <div class="tag-section">
                <h4>Sources</h4>
                <ul class="music-list">${sourcesHtml}</ul>
            </div>

            <div class="tag-disclaimer">⚠️ ${escapeHtml(data.legal_notice || 'Metadata-only analysis.')}</div>
        </div>
    `;
}

function setLoading(state) {
    loading.classList.toggle('hidden', !state);
}

function showError(msg) {
    errorBox.innerHTML = `<span>${escapeHtml(msg)}</span>`;
    errorBox.classList.remove('hidden');
}

function hideError() {
    errorBox.classList.add('hidden');
    errorBox.innerHTML = '';
}

function escapeHtml(value) {
    const str = String(value ?? '');
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
