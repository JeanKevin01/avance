document.addEventListener('DOMContentLoaded', () => {

    // --- CONFIGURACIÓN ---
    const WEBHOOK_URL = 'https://n8n.apps1.astraera.space/webhook/opemip';

    // --- ELEMENTOS DEL DOM (FORMULARIO) ---
    const form = document.getElementById('reporteForm');
    const submitBtn = document.querySelector('.submit-btn');
    const supervisorSelect = document.getElementById('supervisor');
    const supervisorOtroInput = document.getElementById('supervisorOtro');
    const ubicacionSelect = document.getElementById('ubicacion');
    const ubicacionOtroInput = document.getElementById('ubicacionOtro');
    const tipoActividadPrincipal = document.getElementById('tipoActividadPrincipal');
    const dynamicFormsContainer = document.getElementById('dynamic-forms-container');

    // --- TEMPLATES (FORMULARIO) ---
    const templates = {
        limpieza_excavacion: document.getElementById('template-limpieza-excavacion'),
        soporte_compactacion: document.getElementById('template-soporte-compactacion'),
        relleno_filete: document.getElementById('template-relleno-filete'),
        relleno_area: document.getElementById('template-relleno-area')
    };

    // --- MANEJO DE EVENTOS (FORMULARIO) ---
    supervisorSelect.addEventListener('change', () => supervisorOtroInput.classList.toggle('hidden', supervisorSelect.value !== 'Otro'));
    ubicacionSelect.addEventListener('change', () => ubicacionOtroInput.classList.toggle('hidden', ubicacionSelect.value !== 'Otro'));
    tipoActividadPrincipal.addEventListener('change', () => {
        if (tipoActividadPrincipal.value) ensureActivityGroupExists(tipoActividadPrincipal.value);
        tipoActividadPrincipal.value = ''; 
    });
    dynamicFormsContainer.addEventListener('click', handleDynamicFormClick);
    dynamicFormsContainer.addEventListener('change', handleDynamicFormChange);
    form.addEventListener('submit', handleFormSubmit);

    // -------------------------------------------------------------------------------- //
    // --- SECCIÓN DE REGISTROS (HISTORIAL) ---
    // -------------------------------------------------------------------------------- //
    const tabForm = document.getElementById('tab-form');
    const tabHistory = document.getElementById('tab-history');
    const formView = document.getElementById('form-view');
    const historyView = document.getElementById('history-view');
    const historyContainer = document.getElementById('history-container');
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    const historySearchInput = document.getElementById('history-search-input'); // ANOTACIÓN: Elemento del buscador

    tabForm.addEventListener('click', () => switchView('form'));
    tabHistory.addEventListener('click', () => switchView('history'));
    clearHistoryBtn.addEventListener('click', clearHistory);
    historySearchInput.addEventListener('input', handleHistorySearch); // ANOTACIÓN: Evento para buscar en tiempo real

    function switchView(viewName) {
        if (viewName === 'history') {
            formView.classList.add('hidden'); historyView.classList.remove('hidden');
            tabForm.classList.remove('active'); tabHistory.classList.add('active');
            historySearchInput.value = ''; // Limpiamos el buscador al cambiar de pestaña
            loadHistory();
        } else {
            historyView.classList.add('hidden'); formView.classList.remove('hidden');
            tabHistory.classList.remove('active'); tabForm.classList.add('active');
        }
    }

    /**
     * ANOTACIÓN: Nueva función para manejar la búsqueda.
     * Filtra las tarjetas de historial basadas en el texto ingresado.
     */
    function handleHistorySearch() {
        const searchTerm = historySearchInput.value.toLowerCase().trim();
        const reportCards = historyContainer.querySelectorAll('.history-card');
        let visibleCount = 0;

        reportCards.forEach(card => {
            const cardText = card.textContent.toLowerCase();
            const isVisible = cardText.includes(searchTerm);
            card.classList.toggle('hidden', !isVisible);
            if (isVisible) visibleCount++;
        });

        // Muestra u oculta el mensaje de "No hay resultados"
        const noResultsMessage = historyContainer.querySelector('.no-history-message');
        if (noResultsMessage) {
            const showNoResults = visibleCount === 0 && reportCards.length > 0;
            noResultsMessage.textContent = 'No se encontraron resultados para su búsqueda.';
            noResultsMessage.classList.toggle('hidden', !showNoResults);
        }
    }

    function loadHistory() {
        const reports = JSON.parse(localStorage.getItem('dailyReports')) || [];
        historyContainer.innerHTML = '';
        if (reports.length === 0) {
            historyContainer.innerHTML = '<p class="no-history-message">No hay registros guardados.</p>';
            return;
        }
        reports.reverse().forEach(report => historyContainer.appendChild(createHistoryCard(report)));
        historyContainer.insertAdjacentHTML('beforeend', '<p class="no-history-message hidden"></p>'); // Contenedor para mensaje de "no resultados"
    }

    function createHistoryCard(report) {
        const card = document.createElement('div');
        card.className = 'history-card';
        const headerHTML = `
            <div class="history-card-header">
                <p><strong>Fecha:</strong> ${report.fecha}</p>
                <p><strong>Turno:</strong> ${report.turno}</p>
                <p><strong>Supervisor:</strong> ${report.supervisor}</p>
                <p><strong>Ubicación:</strong> ${report.ubicacion}</p>
                <p><strong>Personal Civil:</strong> ${report.personal_total}</p>
            </div>
        `;
        const activitiesByType = report.actividades_realizadas.reduce((acc, activity) => {
            (acc[activity.tipo] = acc[activity.tipo] || []).push(activity);
            return acc;
        }, {});
        let tablesHTML = '';
        for (const tipo in activitiesByType) {
            const activities = activitiesByType[tipo];
            const headers = Object.keys(activities[0]).filter(key => key !== 'tipo');
            tablesHTML += `<h5 class="history-activity-title">${tipo}</h5>`;
            tablesHTML += `<table class="history-table"><thead><tr>`;
            headers.forEach(header => tablesHTML += `<th>${header.charAt(0).toUpperCase() + header.slice(1)}</th>`);
            tablesHTML += `</tr></thead><tbody>`;
            activities.forEach(activity => {
                tablesHTML += `<tr>`;
                headers.forEach(header => {
                    tablesHTML += `<td data-label="${header.charAt(0).toUpperCase() + header.slice(1)}">${activity[header] || ''}</td>`;
                });
                tablesHTML += `</tr>`;
            });
            tablesHTML += `</tbody></table>`;
        }
        card.innerHTML = headerHTML + tablesHTML;
        return card;
    }

    function saveReportToHistory(reportData) {
        const reports = JSON.parse(localStorage.getItem('dailyReports')) || [];
        reports.push(reportData);
        localStorage.setItem('dailyReports', JSON.stringify(reports));
    }

    function clearHistory() {
        if (confirm('¿Estás seguro de que quieres borrar todos los registros?')) {
            localStorage.removeItem('dailyReports');
            loadHistory();
        }
    }

    // --- FUNCIONES DEL FORMULARIO ---
    function handleDynamicFormClick(e) {
        if (e.target.classList.contains('remove-row-btn')) {
            const row = e.target.closest('.data-row'), group = row.closest('.activity-group');
            row.remove();
            if (group.querySelectorAll('.data-row').length === 0) group.remove();
        } else if (e.target.classList.contains('add-row-btn')) {
            const group = e.target.closest('.activity-group');
            addNewRow(group, group.dataset.groupType);
        }
    }
    function handleDynamicFormChange(e) {
        if (e.target.classList.contains('material-select')) {
            const row = e.target.closest('.data-row'), otherInput = row.querySelector('[name="material_otro"]');
            if (otherInput) { otherInput.classList.toggle('hidden', e.target.value !== 'Otro'); otherInput.required = e.target.value === 'Otro'; }
        }
    }
    async function handleFormSubmit(e) {
        e.preventDefault();
        submitBtn.disabled = true; submitBtn.textContent = 'Enviando...';
        const reportData = collectFormData();
        console.log("Enviando datos:", JSON.stringify(reportData, null, 2));
        try {
            const response = await fetch(WEBHOOK_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(reportData) });
            if (response.ok) {
                alert('¡Reporte enviado con éxito!');
                saveReportToHistory(reportData);
                location.reload();
            } else {
                alert(`Error: ${response.status} ${response.statusText}`);
                submitBtn.disabled = false; submitBtn.textContent = 'Enviar Reporte Completo';
            }
        } catch (error) {
            alert(`Error de conexión: ${error.message}`);
            submitBtn.disabled = false; submitBtn.textContent = 'Enviar Reporte Completo';
        }
    }
    function ensureActivityGroupExists(type) {
        let group = dynamicFormsContainer.querySelector(`.activity-group[data-group-type="${type}"]`);
        if (!group) { group = createActivityGroup(type); dynamicFormsContainer.appendChild(group); }
        addNewRow(group, type);
    }
    function createActivityGroup(type) {
        const group = document.createElement('div');
        group.className = 'activity-group';
        group.dataset.groupType = type;
        const title = tipoActividadPrincipal.querySelector(`option[value="${type}"]`).textContent;
        const { headers, gridClass } = getGroupConfig(type);
        group.innerHTML = `<h4 class="group-title">${title}</h4><div class="group-headers ${gridClass}">${headers}</div><div class="rows-wrapper"></div><button type="button" class="add-row-btn">+ Agregar Fila</button>`;
        return group;
    }
    function addNewRow(group, type) {
        const wrapper = group.querySelector('.rows-wrapper'), template = templates[type];
        if (template) {
            const newRow = template.content.cloneNode(true);
            newRow.querySelector('.data-row').classList.add(getGroupConfig(type).gridClass);
            wrapper.appendChild(newRow);
        }
    }
    function getGroupConfig(type) {
        switch (type) {
            case 'limpieza_excavacion': return { headers: '<div>Área</div><div>Avance</div>', gridClass: 'limpieza-excavacion-grid' };
            case 'soporte_compactacion': return { headers: '<div>Material</div><div>Avance</div>', gridClass: 'soporte-compactacion-grid' };
            case 'relleno_filete': return { headers: '<div># Filete</div><div>Capa</div><div>Material</div><div>Avance</div>', gridClass: 'relleno-filete-grid' };
            case 'relleno_area': return { headers: '<div>Área</div><div>Capa</div><div>Material</div><div>Avance</div>', gridClass: 'relleno-area-grid' };
            default: return { headers: '', gridClass: '' };
        }
    }
    function collectFormData() {
        return {
            fecha: document.getElementById('fecha').value,
            turno: document.getElementById('turno').value,
            supervisor: supervisorSelect.value === 'Otro' ? supervisorOtroInput.value.toUpperCase() : supervisorSelect.value,
            ubicacion: ubicacionSelect.value === 'Otro' ? ubicacionOtroInput.value.toUpperCase() : ubicacionSelect.value,
            actividades_realizadas: collectActivities(),
            personal_total: document.getElementById('personal_total').value,
        };
    }
    function collectActivities() {
        const activities = [];
        dynamicFormsContainer.querySelectorAll('.data-row').forEach(row => {
            const group = row.closest('.activity-group'), type = group.dataset.groupType;
            const data = { tipo: tipoActividadPrincipal.querySelector(`option[value="${type}"]`).textContent };
            row.querySelectorAll('input, select').forEach(input => {
                if (!input.name || (input.closest('.hidden') && input.type !== 'select-one')) return;
                let value = input.value;
                if (input.matches('input[type="text"]')) { value = value.toUpperCase(); }
                if (input.name === 'material') {
                    data.material = (value === 'Otro') ? row.querySelector('[name="material_otro"]').value.toUpperCase() : value;
                } else if (input.name !== 'material_otro') {
                    data[input.name] = value;
                }
            });
            activities.push(data);
        });
        return activities;
    }
});