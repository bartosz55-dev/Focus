import SwiftUI

public struct SidebarView: View {
    @ObservedObject var appState: AppState

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Brand Logo Header
            VStack(alignment: .leading, spacing: 2) {
                Text("FOCUS")
                    .font(.system(size: 22, weight: .heavy, design: .rounded))
                    .tracking(2)
                    .foregroundColor(.primary)

                Text("AI VIDEO STUDIO")
                    .font(.system(size: 9, weight: .bold))
                    .tracking(1.5)
                    .foregroundColor(appState.accentColor)
            }
            .padding(.horizontal, 14)
            .padding(.top, 14)

            Divider()
                .padding(.horizontal, 10)

            // Section 1: Workflow
            VStack(alignment: .leading, spacing: 4) {
                Text(appState.localized("workflow"))
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 14)

                SidebarItem(
                    title: appState.localized("tab_generator"),
                    icon: "wand.and.stars",
                    isSelected: appState.currentTab == .generator,
                    accentColor: appState.accentColor
                ) {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                        appState.currentTab = .generator
                    }
                }

                SidebarItem(
                    title: appState.localized("tab_gallery"),
                    icon: "person.crop.artframe",
                    isSelected: appState.currentTab == .gallery,
                    accentColor: appState.accentColor
                ) {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                        appState.currentTab = .gallery
                    }
                }
            }

            // Section 2: Configuration
            VStack(alignment: .leading, spacing: 4) {
                Text(appState.currentLanguage == "Polski" ? "KONFIGURACJA" : "PREFERENCES")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 14)

                SidebarItem(
                    title: appState.currentLanguage == "Polski" ? "Ustawienia" : "Settings",
                    icon: "gearshape.2",
                    isSelected: appState.currentTab == .settings,
                    accentColor: appState.accentColor
                ) {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                        appState.currentTab = .settings
                    }
                }
            }

            Spacer()

            Divider()
                .padding(.horizontal, 10)

            // About Focus Quick Action & Status Footer
            VStack(spacing: 8) {
                Button(action: {
                    appState.showAboutSheet = true
                }) {
                    HStack(spacing: 8) {
                        Image(systemName: "info.circle")
                            .font(.system(size: 12, weight: .medium))
                        Text(appState.currentLanguage == "Polski" ? "O programie Focus" : "About Focus")
                            .font(.system(size: 11, weight: .medium))
                        Spacer()
                    }
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 6, style: .continuous)
                            .fill(Color.white.opacity(0.04))
                    )
                }
                .buttonStyle(AppleSpringButtonStyle())

                HStack {
                    Text("v2.0.0 (macOS Native)")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundColor(.secondary)
                    Spacer()
                    Circle()
                        .fill(appState.isProcessing ? Color.orange : Color.green)
                        .frame(width: 8, height: 8)
                        .shadow(color: (appState.isProcessing ? Color.orange : Color.green).opacity(0.6), radius: 4)
                }
                .padding(.horizontal, 4)
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 12)
        }
        .frame(minWidth: 200, maxWidth: 220)
        .background(.ultraThinMaterial)
    }
}

struct SidebarItem: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let accentColor: Color
    let action: () -> Void
    @State private var isHovered: Bool = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(isSelected ? .white : (isHovered ? .primary : .secondary))
                    .frame(width: 18)

                Text(title)
                    .font(.system(size: 12, weight: isSelected ? .semibold : .regular))
                    .foregroundColor(isSelected ? .white : .primary)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .contentShape(Rectangle())
            .background(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(isSelected ? accentColor : (isHovered ? Color.white.opacity(0.08) : Color.clear))
            )
        }
        .buttonStyle(AppleSpringButtonStyle())
        .padding(.horizontal, 8)
        .onHover { h in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = h
            }
        }
    }
}
