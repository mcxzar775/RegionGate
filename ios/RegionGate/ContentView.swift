import SwiftUI

struct ContentView: View {
    var body: some View {
        NavigationView {
            List {
                Text("节点管理")
                Text("设备绑定")
                Text("连接状态")
            }
            .navigationTitle("RegionGate")
        }
    }
}
