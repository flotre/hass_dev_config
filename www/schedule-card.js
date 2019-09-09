

const LitElement = Object.getPrototypeOf(
    customElements.get("hui-view")
  );
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;


const MODES = {
    eco: {color:'lightblue', label:'Eco'},
    comfort: {color:'red', label:'Confort'},
    away: {color:'green', label:'Absent'}
};

const fetchSchedule = (hass, sid) =>
  hass.callWS({
    type: "schedule_list/fetch",
    schedule_id: sid
  });

const updateSchedule = (
  hass,
  sid,
  s,
  e
) =>
  hass.callWS({
    type: "schedule_list/update",
    schedule_id: sid,
    data: {schedule: [...s], entities:[...e]},
  });




class ScheduleCard extends LitElement {
  
    static getStubConfig() {
      return {};
    }
    static get properties() {
        return {
          schedule: {type: Array},
          hass: {},
          entities: {type: Array},
        };
    }

    constructor() {
        super();
        this._select_start = "";
        this._hours = [];
        this._weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        for(var i=0; i<24; i+=0.5) {
            this._hours.push(i);
        }
        this.mode = "comfort";
    }
  
  
    getCardSize() {
      return (this._config ? (this._config.title ? 1 : 0) : 0) + 3;
    }
  
    setConfig(config) {
      this._config = config;
      if( !config.id ) {
          throw new Error('You need to define an id');
      }
      if( !config.title ) {
        throw new Error('You need to define a title');
      }

      this._fetchData();
      
    }

    connectedCallback() {
        super.connectedCallback();
        this._fetchData();
    }

    disconnectedCallback() {
        super.disconnectedCallback();
    }
  
  
    render() {
      if (!this._config || !this.hass || !this.schedule || !this.entities) {
        return html``;
      }
      console.log("render", this.entities, this.schedule);
      return html`
        <ha-card .header="${this._config.title}">
            <div class="wrapper">
                
                <div class="entete_h"></div>
                
                ${this._hours.map(
                    (item, index) =>
                    html`${index%2==0 ? html`<div id="entete_${index}" class="item hours">${item}</div>` : html``}`
                )}
                
                ${this._weekdays.map(
                    (day, dindex) =>
                    html`<div class="entete">${day}</div>
                    ${this._hours.map(
                        (hour, hindex) =>
                        html`<div id="${dindex}-${hindex}" class="item" style="background-color: ${MODES[this.schedule[dindex][hindex].nval ? this.schedule[dindex][hindex].nval : this.schedule[dindex][hindex].cval].color};"
                                @click="${this._onclick}"
                                @pointerenter="${this._onpointerenter}"
                                >
                                </div>`
                    )}
                    `
                )}
                
            </div>
            <div>
                <label id="label2">Mode:</label>
                ${Object.keys(MODES).map(mode => html`
                <input type="radio" id="${mode}" name="mode" value="${mode}" @change="${this._modeSelected}" ?checked="${this.mode == mode}">
                <label for="${mode}">${MODES[mode].label}</label>
                `)}
            </div>
            <div>
                <paper-dropdown-menu label="Thermostat">
                    <paper-listbox slot="dropdown-content" multi
                        attr-for-selected="itemname"
                        .selectedValues=${this.entities}
                        @click="${this._onclick_thermostat}"
                        >
                            ${this._getThermostat().map(name => html`
                            <paper-item itemname="${name}">${name}</paper-item>
                            `)}
                    </paper-listbox>
                </paper-dropdown-menu>
            </div>
        </ha-card>
      `;
    }
  
    static get styles() {
      return css`
        .wrapper {
            display: grid;
            grid-template-columns: auto repeat(48, 1fr);
            grid-gap: 1px;
        }

        .hours {
            font-size: 10px;
            grid-column-start: span 2;
        }
    
      `;
    }

    async _fetchData() {
        if (this.hass) {
            console.log("prefetch");
            const data = await fetchSchedule(this.hass, this._config.id);
            console.log("fetch", "data=",data);
            // update schedule and entities
            if( data.schedule ) {
                this.entities = [...data.entities];
                this.schedule = [...data.schedule];
            } else if (!this.schedule && !this.entities) {
                this.schedule = Array(this._weekdays.length).fill(0).map(x => Array(this._hours.length).fill(0).map((x) => Object({cval:"eco", nval:""})));
                this.entities = [];
            }
        }
    }

    _updateData() {
        updateSchedule(this.hass, this._config.id, this.schedule, this.entities
        ).catch(() => {console.log("updateSchedule.catch"); this._fetchData()});
        console.log("save");
    }

    _getThermostat() {
        const thermostat = [];
        for( var state in this.hass.states) {
            if( state.startsWith("climate") ) {
                thermostat.push(this.hass.states[state].entity_id);
            }
        }
        return thermostat;
    }

    _setScheduleMode(id, mode, type, schedule) {
        const iday = parseInt(id.split('-')[0], 10);
        const ihours = parseInt(id.split('-')[1], 10);
        schedule[iday][ihours][type] = mode;
    }

    _setScheduleMode2(sid, eid, mode, type, schedule) {
        var sday = parseInt(sid.split('-')[0], 10);
        var shour = parseInt(sid.split('-')[1], 10);
        var eday = parseInt(eid.split('-')[0], 10);
        var ehour = parseInt(eid.split('-')[1], 10);
        if( eday < sday ) {
            const old = sday;
            sday = eday;
            eday = old;
        }
        if( ehour < shour ) {
            const old = shour;
            shour = ehour;
            ehour = old;
        }
        for(var d=sday; d<=eday; d++) {
            for(var h=shour; h<=ehour; h++) {
                schedule[d][h][type] = mode;
            }
        }
    }

    _resetScheduleMode(schedule) {
        schedule.forEach(function(row) {
            row.forEach(function(item) {
                item.nval = "";
            });
        } );
    }

    _onclick(ev) {
        if(ev) {

            if( this._select_start == "" ) {
                const id = ev.target.id;
                this._select_start = id;
                // copy array
                const newschedule = [...this.schedule];
                this._setScheduleMode(id, this.mode, "cval", newschedule);
                this.schedule = newschedule;
            } else {
                this._select_start = "";
                // validate selection
                const newschedule = [...this.schedule];
                newschedule.forEach(function(row) {
                    row.forEach(function(item) {
                        if( item.nval ) {
                            item.cval = item.nval;
                            item.nval = "";
                        }
                    });
                } );
                this.schedule = newschedule;
                // save data
                this._updateData();
            }
        }
    }
    
    _onpointerenter(ev) {
        if( this._select_start ) {
            const eid = ev.target.id;
            const newschedule = [...this.schedule];
            this._resetScheduleMode(newschedule);
            this._setScheduleMode2(this._select_start, eid, this.mode, 'nval', newschedule);
            this.schedule = newschedule;
        }
    }

    _modeSelected(ev) {
        if(ev) {
            this.mode = ev.target.value;
        }
    }

    _onclick_thermostat(ev) {
        this._updateData();
    }
}
  

customElements.define("schedule-card", ScheduleCard);
