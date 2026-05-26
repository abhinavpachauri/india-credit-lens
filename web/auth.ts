import NextAuth from "next-auth";
import Google  from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [Google],
  session:   { strategy: "jwt", maxAge: 30 * 24 * 60 * 60 }, // 30 days
  callbacks: {
    async signIn({ user }) {
      // Logs to Vercel function logs — check dashboard for new subscribers
      console.log(`[icl-signup] ${user.email} at ${new Date().toISOString()}`);
      return true;
    },
    async session({ session, token }) {
      if (token.email) session.user.email = token.email as string;
      return session;
    },
  },
});
