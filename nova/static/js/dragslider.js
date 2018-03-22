(function( $, undefined ) {

$.widget("ui.dragslider", $.ui.slider, {

    options: $.extend({},$.ui.slider.prototype.options,{rangeDrag:true}),

    _create: function() {
        $.ui.slider.prototype._create.apply(this,arguments);
        this._rangeCapture = false;
    },

    _createRange: function( event ) {
        $.ui.slider.prototype._createRange.apply(this,arguments);
        var o = this.options;
        if ( o.range && o.rangeDrag) {
            this.dragIcon = $("<i>").appendTo(this.range);
            this.range.css({
                    "text-align":"center",
                    "font-size":"1.5em",
                    "overflow": "hidden"
                });
            this.dragIcon.css({
                "color": "#aaa",
                "pointer-events":"none"
            });
            if (o.orientation === "horizontal") {
                this._addClass(this.dragIcon, "fa fa-ellipsis-h");
                this.dragIcon.css({
                    "position":"relative",
                    "top":"-11px"
                });
            } else {
                this._addClass(this.dragIcon, "fa fa-ellipsis-v");
                this.range.css({"display": "table"});
                this.dragIcon.css({
                    "display": "table-cell",
                    "vertical-align":"middle"
                });
            }
        }
    },

    _mouseCapture: function( event ) {
        var o = this.options;

        if ( o.disabled ) return false;

        if(event.target == this.range.get(0) && o.rangeDrag && o.range) {
            this._rangeCapture = true;
            this._rangeStart = null;
        }
        else {
            this._rangeCapture = false;
        }

        $.ui.slider.prototype._mouseCapture.apply(this,arguments);

        if(this._rangeCapture == true) {
            this.handles.removeClass("ui-state-active").blur();
        }

        return true;
    },

    _mouseStop: function( event ) {
        this._rangeStart = null;
        return $.ui.slider.prototype._mouseStop.apply(this,arguments);
    },

    _slide: function( event, index, newVal ) {
        if(!this._rangeCapture) {
          return $.ui.slider.prototype._slide.apply(this,arguments);
        }

        if(this._rangeStart == null) {
          this._rangeStart = newVal;
        }

        var oldValueLeft = Number(this.options.values[0]),
            oldValueRight = Number(this.options.values[1]),
            slideDistance = newVal - this._rangeStart,
            newValueLeft = oldValueLeft + slideDistance,
            newValueRight = oldValueRight + slideDistance,
            allowed;

        if ( this.options.values && this.options.values.length ) {
            if(newValueRight > this._valueMax() && slideDistance > 0) {
                slideDistance -= (newValueRight-this._valueMax());
                newValueLeft = oldValueLeft + slideDistance;
                newValueRight = oldValueRight + slideDistance;
            }

            if(newValueLeft < this._valueMin()) {
                slideDistance += (this._valueMin()-newValueLeft);
                newValueLeft = oldValueLeft + slideDistance;
                newValueRight = oldValueRight + slideDistance;
            }

            if ( slideDistance != 0 ) {
                newValues = this.values();
                newValues[ 0 ] = newValueLeft;
                newValues[ 1 ] = newValueRight;

                allowed = this._trigger( "slide", event, {
                    handle: this.handles[ index ],
                    value: slideDistance,
                    values: newValues
                });

                if ( allowed !== false ) {
                    this.values( 0, newValueLeft, true );
                    this.values( 1, newValueRight, true );
                }
                this._rangeStart = newVal;
            }
        }
    },


});

})(jQuery);
