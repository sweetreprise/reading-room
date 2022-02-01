
// logic for working the friends pill tabs
$('#pills-tab').click(function(evt) {
    if (evt.target.id === 'friends-tab') {
        $('#pills-friends').show()
        $('#pills-received').hide()
        $('#pills-sent').hide()
    }
    else if (evt.target.id === 'received-tab') {
        $('#pills-friends').hide()
        $('#pills-received').show()
        $('#pills-sent').hide()
    }
    else if (evt.target.id === 'sent-tab') {
        $('#pills-friends').hide()
        $('#pills-received').hide()
        $('#pills-sent').show()
    }
})



