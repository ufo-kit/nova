Vue.component('searchresults', {
  template: '#search-results-template',
  props: ['show', 'search_query'],
  methods: {
    showFullResults: function() {
      this.$parent.$options.methods.showFullResults()
    }
  }
})

var mainsearch = new Vue ({
  el:'#main-search',
  data: {
    token: readCookie('token'),
    search_query: '',
    search_results: [],
    show_results: false
  },
  watch: {
    search_query: function (data) {
      if (data == '')
        this.hideResults()
      else 
        this.searchQuery(data)
    }
  },
  methods: {
    searchQuery: _.debounce(
      function (query) {
        var params = {
          q: query
        }
        var headers = {
            'Auth-Token': this.token
        }
        this.$http.get('/api/search', {params: params, headers: headers}).then((response) => {
          return response.json();
        }).then((items) => {
          this.search_results = items
          if (items.length >0) this.showResults()
          else this.hideResults()
        })
      },
      250
    ),
    showResults: function() {
      this.show_results = true
    },
    hideResults: function() {
      this.show_results = false
    },
    showFullResults: function(query) {
      window.location = "/search?q="+this.search_query
    },
    clearQuery: function () {
      this.search_query = ''
    },
  },
})

var notification = new Vue ({
  el: '#main-notification',
  data: {
    token: readCookie('token'),
    notifications: []
  },
  created: function() {
    this.loadNotifications()

    setInterval(function() {
      this.loadNotifications()
    }.bind(this), 30000);
  },
  methods: {
    loadNotifications: function() {
      var headers = { 'Auth-Token': this.token }

      this.$http.get('/api/notifications', {headers: headers}).then((response) => {
        this.notifications = response.body.notifications
      })
    },
    dismiss: function(notification_id) {
      var headers = { 'Auth-Token': this.token }

      this.$http.delete('/api/notification/' + notification_id, {headers: headers}).then((response) => {
        this.loadNotifications()
      })
    }
  }
})
