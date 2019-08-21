import {
    html,
    LitElement,
    css
  } from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";
import { repeat } from "https://unpkg.com/lit-html/directives/repeat.js?module";
  

const fetchItems = (hass) =>
  hass.callWS({
    type: "schedule_list/items",
  });

const updateItem = (
  hass,
  itemId,
  item
) =>
  hass.callWS({
    type: "schedule_list/items/update",
    item_id: itemId,
    ...item,
  });

const clearItems = (hass) =>
  hass.callWS({
    type: "schedule_list/items/clear",
  });

const addItem = (
  hass,
  name
) =>
  hass.callWS({
    type: "schedule_list/items/add",
    name,
  });

  
class ScheduleListCard extends LitElement {
  
    static getStubConfig() {
      return {};
    }
    static get properties() {
        return {
          hass: {},
          _config: {},
          _uncheckedItems: [],
          _checkedItems: []
        };
      }
  
  
    getCardSize() {
      return (this._config ? (this._config.title ? 1 : 0) : 0) + 3;
    }
  
    setConfig(config) {
      this._config = config;
      this._uncheckedItems = [];
      this._checkedItems = [];
      this._fetchData();
    }
  
    connectedCallback() {
      super.connectedCallback();
  
      if (this.hass) {
        this._unsubEvents = this.hass.connection.subscribeEvents(
          () => this._fetchData(),
          "schedule_list_updated"
        );
        this._fetchData();
      }
    }
  
    disconnectedCallback() {
      super.disconnectedCallback();
  
      if (this._unsubEvents) {
        this._unsubEvents.then((unsub) => unsub());
      }
    }
  
    render() {
      if (!this._config || !this.hass) {
        return html``;
      }
  
      return html`
        <ha-card .header="${this._config.title}">
          <div class="addRow">
            <ha-icon
              class="addButton"
              @click="${this._addItem}"
              icon="hass:plus"
              .title="Add Item"
            >
            </ha-icon>
            
                <paper-dropdown-menu label="Mode">
                    <paper-listbox slot="dropdown-content" selected="1">
                    <paper-item>eco</paper-item>
                    <paper-item>comfort</paper-item>
                    <paper-item>away</paper-item>
                    </paper-listbox>
                </paper-dropdown-menu>
                <paper-dropdown-menu label="Days">
                    <paper-listbox slot="dropdown-content" selected="1">
                    <paper-item _data="0-6">all</paper-item>
                    <paper-item _data="5-6">Weekend</paper-item>
                    <paper-item _data="0">Lundi</paper-item>
                    <paper-item _data="1">Mardi</paper-item>
                    <paper-item _data="2">Mercredi</paper-item>
                    <paper-item _data="3">Jeudi</paper-item>
                    <paper-item _data="4">Vendredi</paper-item>
                    <paper-item _data="5">Samedi</paper-item>
                    <paper-item _data="6">Dimanche</paper-item>
                    </paper-listbox>
                </paper-dropdown-menu>
            
              <paper-input
                label="Début"
                class="addBox"
                placeholder="mode days starttime"
                @keydown="${this._addKeyPress}"
                type="time"
              ></paper-input>
            
          </div>
          ${repeat(
            this._uncheckedItems,
            (item) => item.id,
            (item, index) =>
              html`
                <div class="editRow">
                  <paper-checkbox
                    slot="item-icon"
                    id="${index}"
                    ?checked="${item.enable}"
                    .itemId="${item.id}"
                    @click="${this._completeItem}"
                    tabindex="0"
                  ></paper-checkbox>
                  <paper-dropdown-menu label="Mode">
                    <paper-listbox slot="dropdown-content" selected="1">
                    <paper-item>eco</paper-item>
                    <paper-item>comfort</paper-item>
                    <paper-item>away</paper-item>
                    </paper-listbox>
                </paper-dropdown-menu>
                  <paper-item-body>
                    <paper-input
                      no-label-float
                      .value="${item.name}"
                      .itemId="${item.id}"
                      @change="${this._saveEdit}"
                    ></paper-input>
                  </paper-item-body>
                </div>
              `
          )}
          ${this._checkedItems.length > 0
            ? html`
                <div class="divider"></div>
                <div class="checked">
                  <span class="label">
                    checked label
                  </span>
                  <ha-icon
                    class="clearall"
                    @click="${this._clearItems}"
                    icon="hass:notification-clear-all"
                    .title="Clear item"
                  >
                  </ha-icon>
                </div>
                ${repeat(
                  this._checkedItems,
                  (item) => item.id,
                  (item, index) =>
                    html`
                      <div class="editRow">
                        <paper-checkbox
                          slot="item-icon"
                          id="${index}"
                          ?checked="${item.enable}"
                          .itemId="${item.id}"
                          @click="${this._completeItem}"
                          tabindex="0"
                        ></paper-checkbox>
                        <paper-dropdown-menu label="Mode">
                            <paper-listbox slot="dropdown-content" selected="1">
                            <paper-item>eco</paper-item>
                            <paper-item>comfort</paper-item>
                            <paper-item>away</paper-item>
                            </paper-listbox>
                        </paper-dropdown-menu>
                        <paper-item-body>
                          <paper-input
                            no-label-float
                            .value="${item.name}"
                            .itemId="${item.id}"
                            @change="${this._saveEdit}"
                          ></paper-input>
                        </paper-item-body>
                      </div>
                    `
                )}
              `
            : ""}
        </ha-card>
      `;
    }
  
    static get styles() {
      return css`
        .editRow,
        .addRow {
          display: flex;
          flex-direction: row;
          align-items: center;
        }
  
        .addButton {
          padding: 9px 15px 11px 15px;
          cursor: pointer;
        }
  
        paper-item-body {
          width: 75%;
        }
  
        paper-checkbox {
          padding: 11px 11px 11px 18px;
        }
  
        paper-input {
          --paper-input-container-underline: {
            display: none;
          }
          --paper-input-container-underline-focus: {
            display: none;
          }
          --paper-input-container-underline-disabled: {
            display: none;
          }
          position: relative;
          top: 1px;
        }
  
        .checked {
          margin-left: 17px;
          margin-bottom: 11px;
          margin-top: 11px;
        }
  
        .label {
          color: var(--primary-color);
        }
  
        .divider {
          height: 1px;
          background-color: var(--divider-color);
          margin: 10px;
        }
  
        .clearall {
          cursor: pointer;
          margin-bottom: 3px;
          float: right;
          padding-right: 10px;
        }
  
        .addRow > ha-icon {
          color: var(--secondary-text-color);
        }
      `;
    }
  
    async _fetchData() {
      if (this.hass) {
        const checkedItems = [];
        const uncheckedItems = [];
        const items = await fetchItems(this.hass);
        for (const key in items) {
          if (items[key].enable) {
            checkedItems.push(items[key]);
          } else {
            uncheckedItems.push(items[key]);
          }
        }
        this._checkedItems = checkedItems;
        this._uncheckedItems = uncheckedItems;
      }
    }
  
    _completeItem(ev) {
      updateItem(this.hass, ev.target.itemId, {
        enable: ev.target.checked,
      }).catch(() => this._fetchData());
      console.log("_completeItem");
    }
  
    _saveEdit(ev) {
      updateItem(this.hass, ev.target.itemId, {
        name: ev.target.value,
      }).catch(() => this._fetchData());
      console.log("_saveEdit");
  
      ev.target.blur();
    }
  
    _clearItems() {
      if (this.hass) {
        console.log("_clearItems");
        clearItems(this.hass).catch(() => this._fetchData());
      }
    }
  
    get _newItem() {
      return this.shadowRoot.querySelector(".addBox");
    }
  
    _addItem(ev) {
      const newItem = this._newItem;
  
      if (newItem.value.length > 0) {
        console.log("_addItem");
        addItem(this.hass, newItem.value).catch(() => this._fetchData());
      }
  
      newItem.value = "";
      if (ev) {
        newItem.focus();
      }
    }
  
    _addKeyPress(ev) {
      if (ev.keyCode === 13) {
        console.log("_addKeyPress");
        this._addItem(null);
      }
    }
}
  

customElements.define("schedule-list-card", ScheduleListCard);
