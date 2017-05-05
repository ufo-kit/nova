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
          if (items.length > 0) this.showResults()
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
    showDataset: function(item) {
      window.location = item.url
    },
    showFullResults: function(query) {
      window.location = "/search?q=" + this.search_query
    },
    clearQuery: function () {
      this.search_query = ''
    },
  },
  directives: {
    'click-outside': {
      bind: function(el, binding, vnode) {
        const handler = (e) => {
          if (!el.contains(e.target) && el !== e.target) {
            binding.value(e)
          }
        }
        el.__vueClickOutside__ = handler

        document.addEventListener('click', handler)
      },
      unbind: function(el, binding) {
        document.removeEventListener('click', el.__vueClickOutside__)
          el.__vueClickOutside__ = null
      }
    }
  }
})


Vue.component('notification-item', {
  props: ['notification'],
  template: `
    <li>
      <div class="row">
        <div class="col-md-1"><span><i class="fa" v-bind:class="notificationClass"></i></span></div>
        <div class="col-md-9">{{ notification.message }}</div>
        <div class="col-md-1"><span class="clickable" @click="dismiss(notification.id)"><i class="fa fa-remove"></i></span></div>
      </div>
    </li>`,
  data: function () {
    return { }
  },
  methods: {
    dismiss: function (notification_id) {
      console.log(notification_id)
      this.$emit('dismiss', notification_id)
    }
  },
  computed: {
    notificationClass: function () {
      switch (this.notification.type) {
        case 'message':
          return 'fa-envelope-open-o'
        case 'review':
          return 'fa-pencil'
        case 'bookmark':
          return 'fa-bookmark'
        default:
          return 'fa-questions'
      }
    }
  }
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
    loadNotifications: function () {
      var headers = { 'Auth-Token': this.token }

      this.$http.get('/api/notifications', {headers: headers}).then((response) => {
        this.notifications = response.body.notifications
      })
    },
    dismissNotification: function (notification_id) {
      var headers = { 'Auth-Token': this.token }

      this.$http.delete('/api/notification/' + notification_id, {headers: headers}).then((response) => {
        this.loadNotifications()
      })
    },
    dismissAllNotifications: function () {
      var headers = { 'Auth-Token': this.token }
      var ids = []

      for (var i = 0; i < this.notifications.length; i++) {
        ids.push(this.notifications[i].id)
      }

      this.$http.patch('/api/notifications', {ids: ids}, {headers: headers}).then((response) => {
        this.loadNotifications()
      })
    }
  }
})
