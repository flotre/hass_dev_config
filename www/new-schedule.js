

const LitElement = Object.getPrototypeOf(
    customElements.get("hui-view")
  );
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;



console.log(customElements);

const MODES = {
    eco: {color:'lightblue', label:'Eco'},
    comfort: {color:'red', label:'Confort'},
    away: {color:'green', label:'Absent'}
};



class ScheduleCard extends LitElement {
  
    static getStubConfig() {
      return {};
    }
    static get properties() {
        return {
          schedule: {type: Array},
        };
    }

    constructor() {
        super();
        this._select_start = '';
        this._hours = [];
        this._weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        for(var i=0; i<24; i+=0.5) {
            this._hours.push(i);
        }
        this.schedule = Array(this._weekdays.length).fill(0).map(x => Array(this._hours.length).fill(0).map((x) => Object({cval:'eco', nval:''})));
    }
  
  
    getCardSize() {
      return (this._config ? (this._config.title ? 1 : 0) : 0) + 3;
    }
  
    setConfig(config) {
      this._config = config;
      
    }

    _pad(d) {
        return (d < 10) ? '0' + d.toString() : d.toString();
    }
  
  
    render() {
      if (!this._config || !this.hass) {
        return html``;
      }
  
      return html`
        <ha-card .header="${this._config.title}">
            <div class="wrapper">
                
                <div class="entete_h"></div>
                
                ${this._hours.map(
                    (item, index) =>
                    html`${index%2==0 ? html`<div id="entete_${index}" class="item hours">${item}</div>` : ''}`
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
                <input type="radio" id="${mode}" name="mode" value="${mode}" @change="${this._modeSelected}" checked>
                <label for="${mode}">${MODES[mode].label}</label>
                `)}
            </div>
            <div>
                <paper-dropdown-menu label="Thermostat">
                    <paper-listbox slot="dropdown-content" multi>
                        ${this._getThermostat().map(name => html`
                        <paper-item>${name}</paper-item>
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

    _setScheduleMode(sid, eid, mode, type, schedule) {
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
                item.nval = '';
            });
        } );
    }

    _onclick(ev) {
        if(ev) {

            if( this._select_start == '' ) {
                const id = ev.target.id;
                this._select_start = id;
                // copy array
                const newschedule = [...this.schedule];
                this._setScheduleMode(id, this.mode, 'cval', newschedule);
                this.schedule = newschedule;
            } else {
                this._select_start = '';
                // validate selection
                const newschedule = [...this.schedule];
                newschedule.forEach(function(row) {
                    row.forEach(function(item) {
                        if( item.nval ) {
                            item.cval = item.nval;
                        }
                    });
                } );
                this.schedule = newschedule;
            }
        }
    }


    _onpointerdown(ev) {
    }
  
    _onpointerup(ev) {
        
    }
    
    _onpointerenter(ev) {
        if( this._select_start ) {
            const eid = ev.target.id;
            const newschedule = [...this.schedule];
            this._resetScheduleMode(newschedule);
            this._setScheduleMode(this._select_start, eid, this.mode, 'nval', newschedule);
            this.schedule = newschedule;
        }
    }

    _modeSelected(ev) {
        if(ev) {
            this.mode = ev.target.value;
        }
    }
}
  

customElements.define("schedule-card", ScheduleCard);
