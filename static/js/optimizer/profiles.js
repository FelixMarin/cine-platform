// profiles.js - Gestión de perfiles de optimización

let currentProfile = 'balanced';

const profileIcons = {
    'ultra_fast': '⚡',
    'fast': '🚀',
    'balanced': '⚖️',
    'high_quality': '🎯',
    'master': '💎'
};

const profileColors = {
    'ultra_fast': '#28a745',
    'fast': '#17a2b8',
    'balanced': '#ffc107',
    'high_quality': '#fd7e14',
    'master': '#dc3545'
};

const profileNames = {
    'ultra_fast': 'Ultra Rápido',
    'fast': 'Rápido',
    'balanced': 'Balanceado',
    'high_quality': 'Alta Calidad',
    'master': 'Master'
};

function loadProfiles() {
    console.log('📥 Cargando perfiles...');

    $.ajax({
        url: '/optimizer/profiles',
        method: 'GET',
        success: function (profiles) {
            console.log('✅ Perfiles cargados:', profiles);
            renderProfiles(profiles);
            setTimeout(() => selectProfile('balanced'), 100);
        },
        error: function (xhr, status, error) {
            console.error('❌ Error cargando perfiles:', error);
            $('#profile-container').html(`
                <div class="col-12">
                    <div class="alert alert-danger">
                        Error cargando perfiles. Por favor, recarga la página.
                    </div>
                </div>
            `);
        }
    });
}

function renderProfiles(profiles) {
    const $container = $('#profile-container');
    $container.empty();

    Object.entries(profiles).forEach(([key, profile]) => {
        const icon = profileIcons[key] || '🎬';
        const color = profileColors[key] || '#6c757d';
        const name = profileNames[key] || key;
        const description = profile.description || '';
        const preset = profile.preset || 'medium';
        const crf = profile.crf || 23;
        const resolution = profile.resolution || 'Auto';

        const col = $('<div>').addClass('col-md-4 col-sm-6 mb-3');
        const card = $(`
            <div class="profile-card" data-profile="${key}">
                <div class="profile-icon" style="color: ${color}">${icon}</div>
                <div class="profile-title">${name}</div>
                <div class="profile-description">${description}</div>
                <div>
                    <span class="profile-badge badge-speed">${preset}</span>
                    <span class="profile-badge badge-quality">CRF ${crf}</span>
                    <span class="profile-badge badge-size">${resolution}</span>
                </div>
            </div>
        `);

        card.on('click', () => selectProfile(key));
        col.append(card);
        $container.append(col);
    });
}

function selectProfile(profile) {
    console.log('📌 Perfil seleccionado:', profile);
    $('.profile-card').removeClass('selected');
    $(`.profile-card[data-profile="${profile}"]`).addClass('selected');
    currentProfile = profile;

    if (window.optimizerUpload && window.optimizerUpload.selectedFile) {
        window.optimizerUpload.estimateSize(window.optimizerUpload.selectedFile);
    }
}

// Exportar
window.optimizerProfiles = {
    currentProfile,
    loadProfiles,
    selectProfile
};