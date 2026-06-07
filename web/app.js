const USE_API = true;
const API_URL = "../backend/api.php";
const DATA_FILE = "../data/cultos.json";
const DATA_URL = USE_API ? API_URL : DATA_FILE;

const FILTER_INPUT = document.querySelector("#filter-input");
const CULTOS_CONTAINER = document.querySelector("#cultos-list");
const SUMMARY = document.querySelector("#summary");
const EMPTY_STATE = document.querySelector("#empty-state");

const MUSIC_FIELDS = [
  { label: "Louvor 1", song: "MUSICA1", singer: "CANTOR_2", tone: "TOM_2" },
  { label: "Louvor 2", song: "MUSICA2", singer: "CANTOR_3", tone: "TOM_3" },
  { label: "Louvor 3", song: "MUSICA3", singer: "CANTOR_4", tone: "TOM_4" },
  { label: "Oferta / Intercessão", song: "MUSICA", singer: "CANTOR_5", tone: "TOM_5" },
  { label: "Pão", song: "MUSICA_PAO", singer: "CANTOR_7", tone: "TOM_7" },
  { label: "Vinho", song: "MUSICA_VINHO", singer: "CANTOR_8", tone: "TOM_8" },
  { label: "Extra", song: "MUSICA_EXTRA", singer: "CANTOR_9", tone: "TOM_9" },
  { label: "Final", song: "MUSICA_FINAL", singer: "CANTOR_10", tone: "TOM_10" },
];
const MUSIC_FORM_FIELDS = [
  { label: "Louvor 1", song: "musica1", singer: "cantor1", tone: "tom1" },
  { label: "Louvor 2", song: "musica2", singer: "cantor2", tone: "tom2" },
  { label: "Louvor 3", song: "musica3", singer: "cantor3", tone: "tom3" },
  { label: "Oferta / Intercessão", song: "musica_oferta", singer: "cantor_oferta", tone: "tom_oferta" },
  { label: "Pão", song: "musica_pao", singer: "cantor_pao", tone: "tom_pao" },
  { label: "Vinho", song: "musica_vinho", singer: "cantor_vinho", tone: "tom_vinho" },
  { label: "Extra", song: "musica_extra", singer: "cantor_extra", tone: "tom_extra" },
  { label: "Final", song: "musica_final", singer: "cantor_final", tone: "tom_final" },
];

const formatter = new Intl.DateTimeFormat("pt-BR", {
  weekday: "long",
  day: "2-digit",
  month: "long",
  year: "numeric",
});

let cultos = [];
let fetchError = "";
const NEW_CULTO_FORM = document.querySelector("#new-culto-form");
const FORM_STATUS = document.querySelector("#form-status");
const MUSIC_FIELDS_CONTAINER = document.querySelector("#music-fields");

const renderMusicFormFields = () => {
  if (!MUSIC_FIELDS_CONTAINER) {
    return;
  }
  MUSIC_FIELDS_CONTAINER.innerHTML = "";
  MUSIC_FORM_FIELDS.forEach(({ label, song, singer, tone }) => {
    const group = document.createElement("div");
    group.className = "row g-3 border-top pt-3 mt-3";
    group.innerHTML = `
      <div class="col-12">
        <p class="h6 mb-1">${label}</p>
      </div>
      <div class="col-md-6 col-lg-4">
        <label class="form-label" for="${song}">Nome da música</label>
        <input id="${song}" name="${song}" class="form-control" type="text">
      </div>
      <div class="col-md-6 col-lg-4">
        <label class="form-label" for="${singer}">Cantor / conjunto</label>
        <input id="${singer}" name="${singer}" class="form-control" type="text">
      </div>
      <div class="col-md-6 col-lg-4">
        <label class="form-label" for="${tone}">Tom</label>
        <input id="${tone}" name="${tone}" class="form-control" type="text">
      </div>`;
    MUSIC_FIELDS_CONTAINER.appendChild(group);
  });
};

const showFormStatus = (message, variant = "success") => {
  if (!FORM_STATUS) {
    return;
  }
  const classesToClean = ["alert-success", "alert-danger", "alert-warning", "alert-info"];
  FORM_STATUS.classList.remove("visually-hidden");
  classesToClean.forEach((cls) => FORM_STATUS.classList.remove(cls));
  FORM_STATUS.classList.add(`alert-${variant}`);
  FORM_STATUS.textContent = message;
};

const hideFormStatus = () => {
  if (!FORM_STATUS) {
    return;
  }
  FORM_STATUS.classList.add("visually-hidden");
};

const collectFormPayload = () => {
  if (!NEW_CULTO_FORM) {
    return {};
  }
  const payload = {};
  const formData = new FormData(NEW_CULTO_FORM);
  formData.forEach((value, key) => {
    const text = typeof value === "string" ? value.trim() : value;
    payload[key] = text === "" ? null : text;
  });
  return payload;
};

const submitNewCulto = async (event) => {
  event.preventDefault();
  hideFormStatus();
  if (!NEW_CULTO_FORM) {
    return;
  }
  const payload = collectFormPayload();
  try {
    showFormStatus("Enviando culto para o backend...", "info");
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || "Falha ao gravar no banco de dados");
    }
    showFormStatus("Culto cadastrado com sucesso.", "success");
    NEW_CULTO_FORM.reset();
    await fetchCultos();
  } catch (error) {
    showFormStatus(`Erro ao salvar: ${error.message}`, "danger");
  }
};

const fetchCultos = async () => {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) {
      throw new Error("não foi possível carregar os dados");
    }
    const data = await res.json();
    fetchError = "";
    cultos = (data.cultos || []).map(normalizeCulto);
    render();
  } catch (error) {
    fetchError = `Erro ao carregar os dados: ${error.message}`;
    cultos = [];
    render();
  }
};

const normalizeCulto = (record) => {
  const raw = {};
  Object.entries(record).forEach(([key, value]) => {
    raw[key.toUpperCase()] = value;
  });
  return {
    raw,
    date_text: raw.DATA || raw.DATA_TEXTO || raw.DATA_TEXT || raw.DATE_TEXT || "",
    date_iso: record.date_iso || record.data_iso || record.DATE_ISO || "",
  };
};

const formatDate = (value) => {
  if (!value) return "data nao registrada";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : formatter.format(parsed);
};

const createMusicList = (culto) => {
  const list = document.createElement("ul");
  list.className = "list-unstyled card-music mb-0";
  MUSIC_FIELDS.forEach(({ label, song, singer, tone }) => {
    const title = culto.raw[song];
    if (!title) return;
    const item = document.createElement("li");
    item.innerHTML = `
      <span>${label}:</span> ${title}
      ${culto.raw[singer] ? `- ${culto.raw[singer]}` : ""}
      ${culto.raw[tone] ? `<small class="text-muted">(${culto.raw[tone]})</small>` : ""}
    `;
    list.appendChild(item);
  });
  return list.children.length ? list : null;
};

const createCultoCard = (culto) => {
  const card = document.createElement("article");
  card.className = "col-12 col-md-6 col-lg-4";
  card.innerHTML = `
    <div class="card shadow-sm h-100">
      <div class="card-body d-flex flex-column gap-2">
        <h3 class="h6 mb-1">${formatDate(culto.date_iso)}</h3>
        <p class="mb-1"><strong>Dirigente:</strong> ${culto.raw["DIRIGENTE"] || "—"}</p>
        <p class="mb-1"><strong>Preludio:</strong> ${culto.raw["PRELUDIO"] || "—"}</p>
        <p class="mb-1"><strong>Pregador:</strong> ${culto.raw["PREGADOR"] || "—"}</p>
        <div class="card-section text-muted small">
          <p class="mb-1"><strong>Referencias:</strong> ${culto.raw["REF"] || "—"}</p>
          <p class="mb-0"><strong>Texto-base:</strong> ${culto.raw["TEXTO"] || "—"}</p>
        </div>
      </div>
    </div>
  `;

  const musicList = createMusicList(culto);
  if (musicList) {
    const musicWrapper = document.createElement("div");
    musicWrapper.className = "card-footer border-0 pt-0";
    musicWrapper.appendChild(musicList);
    card.querySelector(".card").appendChild(musicWrapper);
  }

  return card;
};

const render = () => {
  const term = FILTER_INPUT.value.trim().toLowerCase();
  const filtered = term
    ? cultos.filter((culto) => {
        const haystack = [
          culto.date_text,
          culto.raw["DIRIGENTE"],
          culto.raw["PREGADOR"],
          culto.raw["PRELUDIO"],
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(term);
      })
    : cultos;

  CULTOS_CONTAINER.innerHTML = "";
  if (filtered.length === 0) {
    EMPTY_STATE.classList.remove("visually-hidden");
  } else {
    EMPTY_STATE.classList.add("visually-hidden");
    filtered.forEach((culto) => CULTOS_CONTAINER.appendChild(createCultoCard(culto)));
  }
  if (fetchError) {
    SUMMARY.textContent = fetchError;
  } else {
    SUMMARY.textContent = `Total: ${cultos.length} cultos - exibindo ${filtered.length} entradas.`;
  }
};

const init = () => {
  renderMusicFormFields();
  NEW_CULTO_FORM?.addEventListener("submit", submitNewCulto);
  fetchCultos();
};

FILTER_INPUT.addEventListener("input", () => render());

init();
