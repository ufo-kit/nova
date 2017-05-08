Vue.component('confirmpublicaccess', {
  template: '#modal-template',
  props: ['show']
})
Vue.component('confirmdirectaccess', {
  template: '#modal-template',
  props: ['show']
})
var accessgrant = new Vue ({
  el:'#access-grant',
  data: {
    token: readCookie('token'),
    read: permissions.read,
    interact: permissions.interact,
    fork: permissions.fork,
  },
  watch: {
    read: function() {
      if (!this.read) this.interact = false
    },
    interact: function() {
      if (this.interact) this.read = true
      else this.fork = false
    },
    fork: function() {
      if (this.fork) this.interact = true
    }
  },
  methods: {
    onGrantAccess: function() {
      var headers = { 'Auth-Token': this.token }
      var access = {'action': 'grant', 'read': this.read, 'interact': this.interact, 'fork': this.fork}
      var api_str = '/api/datasets/' + collection_name + '/' + dataset_name + '/request/' + request_id
      this.$http.patch(api_str, access, {headers: headers}).then((response) => {
        if (response.status == 200 || response.status == 201)
          window.location = '/'
      })
    },
    onDenyAccess: function() {
      var headers = { 'Auth-Token': this.token }
      var api_str = '/api/datasets/' + collection_name + '/' + dataset_name + '/request/' + request_id
      this.$http.delete(api_str, {headers: headers}).then((response) => {
        if (response.status == 200)
          window.location = '/'
      })
    },
  }
})
