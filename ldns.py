from Ixal import Unit

class UnitLdns(Unit):
    name = 'ldns'
    ver = '1.7.1'
    rel = '1'
    desc = "Mainly for drill"
    arch = 'x86_64'
    src = "https://www.nlnetlabs.nl/downloads/ldns/ldns-{}.tar.gz".format(ver)

    def patch(self):
        pass

    def build(self):
        pass

    def pack(self):
        pass

if __name__ == '__main__':
    UnitLdns().make()
    
