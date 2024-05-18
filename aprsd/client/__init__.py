from aprsd.client import aprsis, factory, fake, kiss


TRANSPORT_APRSIS = "aprsis"
TRANSPORT_TCPKISS = "tcpkiss"
TRANSPORT_SERIALKISS = "serialkiss"
TRANSPORT_FAKE = "fake"


client_factory = factory.ClientFactory()
client_factory.register(aprsis.APRSISClient)
client_factory.register(kiss.KISSClient)
client_factory.register(fake.APRSDFakeClient)
